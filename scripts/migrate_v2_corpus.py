#!/usr/bin/env python3
"""Script de migración oficial para Etapa 1 - Iteración 2:
Refactorización de la gestión documental y versionamiento.

Adapta la base de datos SQLite y el modelo documental de versiones globales únicas
a una jerarquía de Categorías Documentales -> Familias Documentales -> Versiones Documentales.
Detecta discrepancias de identidad documental (SHA-256) e inicializa el corpus institucional.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Agregar raíz del proyecto al path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from normativa.config import settings
from normativa.corpus.db import init_db


def run_migration(db_path: Path | str | None = None) -> None:
    target_path = Path(db_path) if db_path else Path(settings.SQLITE_PATH)
    print(f"=== INICIANDO MIGRACIÓN DOCUMENTAL ETAPA 1: {target_path} ===")

    # 1. Asegurar respaldo previo
    backup_dir = PROJECT_ROOT / "data" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"normativa_pre_v2_migration_{timestamp}.db"

    if target_path.exists():
        shutil.copy(target_path, backup_path)
        print(f"[1/5] Respaldo de seguridad creado en: {backup_path}")
    else:
        print(f"[1/5] No existía base de datos en {target_path}. Se creará nueva.")

    # 2. Inicializar tablas e índices de nueva arquitectura
    print("[2/5] Ejecutando creación y actualización de esquemas (DDL)...")
    init_db(target_path)

    # 3. Clasificación de versiones anteriores e identificación de discrepancias
    print("[3/5] Analizando documentos y versiones para asignación de familias e inconsistencias...")
    now = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row

    # Asignar versiones huérfanas a la familia RTG
    conn.execute("UPDATE versions SET family_id = 'fam_reglamento_tg' WHERE family_id IS NULL OR family_id = ''")

    # Analizar huellas SHA-256 para detectar si un documento etiquetado como 2021 usa el PDF de 2019
    docs = conn.execute("SELECT v.id AS ver_id, v.nombre, v.anio, v.numero_acuerdo, d.file_hash FROM versions v JOIN documents d ON v.document_id = d.id").fetchall()
    hash_map: dict[str, list[sqlite3.Row]] = {}
    for d in docs:
        hash_map.setdefault(d["file_hash"], []).append(d)

    for fhash, ver_list in hash_map.items():
        if len(ver_list) > 1:
            print(f"  -> Detectadas versiones con hash SHA-256 compartido ({fhash[:12]}...): {[v['ver_id'] for v in ver_list]}")
            # Si una versión afirma ser 2021 pero comparte hash con la 2019
            has_2019 = any(v["anio"] == 2019 or (v["numero_acuerdo"] and "01-021" in v["numero_acuerdo"]) for v in ver_list)
            for v in ver_list:
                if (v["anio"] == 2021 or (v["numero_acuerdo"] and "01-026" in v["numero_acuerdo"])) and has_2019:
                    print(f"  [DISCREPANCIA IDENTIFICADA] La versión '{v['ver_id']}' está etiquetada como 2021 pero su PDF corresponde al Acuerdo 01-021 de 2019.")
                    conn.execute(
                        """
                        UPDATE versions
                        SET inconsistencia_identidad = 1,
                            estado_revision = 'CON_DISCREPANCIAS',
                            status_message = 'Discrepancia de identidad documental detectada: Huella SHA-256 idéntica a la versión 2019 (Acuerdo 01-021). No corresponde al Acuerdo 01-026 de 2021.',
                            is_active = 0,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (now, v["ver_id"]),
                    )

    # Asegurar que uts_tg_2019 queda como versión activa aprobada de fam_reglamento_tg
    row_2019 = conn.execute("SELECT id, status FROM versions WHERE id = 'uts_tg_2019'").fetchone()
    if row_2019 and row_2019["status"] == "PROCESADO":
        conn.execute(
            """
            UPDATE versions
            SET is_active = 1,
                estado_revision = 'APROBADO',
                activated_at = ?,
                updated_at = ?
            WHERE id = 'uts_tg_2019'
            """,
            (now, now),
        )
        print("  -> Versión legítima 'uts_tg_2019' configurada como activa y aprobada para 'fam_reglamento_tg'.")

    # 4. Actualizar chunks con categoria_id y family_id
    print("[4/5] Propagando categoria_id y family_id a los chunks existentes...")
    conn.execute(
        """
        UPDATE chunks
        SET family_id = (SELECT versions.family_id FROM versions WHERE versions.id = chunks.version_id),
            categoria_id = (
                SELECT families.categoria_id
                FROM versions
                JOIN families ON versions.family_id = families.id
                WHERE versions.id = chunks.version_id
            )
        WHERE chunks.family_id IS NULL OR chunks.categoria_id IS NULL;
        """
    )

    # 5. Migrar trazas históricas para conservar versiones autorizadas
    print("[5/5] Preservando trazas de consulta históricas...")
    traces = conn.execute("SELECT id, version_id, authorized_versions_json FROM traces").fetchall()
    for t in traces:
        if not t["authorized_versions_json"] or t["authorized_versions_json"] == "[]":
            v_val = t["version_id"]
            auth_list = [v_val] if v_val else []
            conn.execute(
                "UPDATE traces SET authorized_versions_json = ? WHERE id = ?",
                (json.dumps(auth_list), t["id"]),
            )

    conn.commit()
    conn.close()
    print("=== MIGRACIÓN COMPLETADA EXITOSAMENTE ===")


if __name__ == "__main__":
    db_file = sys.argv[1] if len(sys.argv) > 1 else None
    run_migration(db_file)
