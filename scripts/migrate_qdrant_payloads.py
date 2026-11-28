"""scripts/migrate_qdrant_payloads.py

Script idempotente y seguro para migrar los payloads de Qdrant con los nuevos campos
``family_id`` y ``categoria_id`` introducidos en la Etapa 1.

Características:
  - Reutiliza la configuración oficial de la aplicación (normativa.config.settings).
  - Utiliza el cliente oficial ``qdrant_client.QdrantClient``.
  - Valida TODAS las relaciones y correspondencias ANTES de escribir (pre-validación).
  - Si se detecta cualquier inconsistencia (puntos huérfanos, desajustes de versión),
    aborta antes de realizar cualquier modificación.
  - Modo --dry-run: simula y contabiliza todas las actualizaciones previstas sin escribir.
  - Modo --verify: modo solo lectura de comprobación.
  - Actualiza únicamente los metadatos necesarios (family_id, categoria_id) mediante
    set_payload con wait=True como parámetro oficial.
  - Preserva identificadores, textos, vectores y demás metadatos.
  - Incluye versiones históricas (no activas).
  - No modifica estados de activación en SQLite ni en Qdrant.
  - Idempotente: puntos con los valores correctos se contabilizan como "ya correctos".
  - Registra: inspeccionados, pendientes, ya correctos, actualizados, inconsistentes y fallidos.
  - Finaliza con código de salida != 0 si existen inconsistencias o actualizaciones fallidas.

Uso::

    # Simulación sin aplicar cambios (dry-run):
    uv run python scripts/migrate_qdrant_payloads.py --dry-run

    # Solo validación de lectura:
    uv run python scripts/migrate_qdrant_payloads.py --verify

    # Aplicación real de la migración:
    uv run python scripts/migrate_qdrant_payloads.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient

from normativa.config import settings


# ---------------------------------------------------------------------------
# Helpers SQLite
# ---------------------------------------------------------------------------

def load_sqlite_chunks(db_path: str | Path) -> dict[str, dict[str, Any]]:
    """Construye un mapa en memoria chunk_id -> metadatos para todos los chunks del corpus,
    incluyendo versiones históricas. Abre una única conexión.
    """
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Base de datos SQLite no encontrada en '{path}'")

    import sqlite3
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                ch.id          AS chunk_id,
                ch.version_id,
                ch.document_id,
                ch.texto,
                v.family_id,
                f.categoria_id
            FROM chunks ch
            JOIN versions v ON ch.version_id = v.id
            JOIN families f ON v.family_id = f.id
            """
        ).fetchall()
        return {r["chunk_id"]: dict(r) for r in rows}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Helpers Qdrant
# ---------------------------------------------------------------------------

def get_qdrant_client(url: str) -> QdrantClient:
    try:
        client = QdrantClient(url=url)
        client.get_collections()
        return client
    except Exception as exc:
        raise ConnectionError(f"No se pudo conectar a Qdrant en '{url}': {exc}") from exc


def scroll_all_points(client: QdrantClient, collection_name: str, batch_size: int = 100):
    """Generador que itera sobre todos los puntos de la colección."""
    offset = None
    while True:
        result, next_offset = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in result:
            yield point
        if next_offset is None:
            break
        offset = next_offset


# ---------------------------------------------------------------------------
# Migración / Verificación principal
# ---------------------------------------------------------------------------

def run_migration(
    qdrant_url: str | None = None,
    collection_name: str | None = None,
    db_path: str | Path | None = None,
    dry_run: bool = False,
    verify_only: bool = False,
    client: QdrantClient | None = None,
) -> tuple[int, dict[str, int]]:
    """Ejecuta la migración o verificación de payloads.

    Retorna:
        (exit_code, statistics_dict)
        exit_code: 0 si todo fue exitoso y consistente; 1 en caso de inconsistencias o fallos.
    """
    url = qdrant_url or settings.QDRANT_URL
    collection = collection_name or settings.QDRANT_COLLECTION
    sqlite_file = db_path or settings.SQLITE_PATH

    print(f"[CONFIG] Qdrant URL   : {url}")
    print(f"[CONFIG] Colección    : {collection}")
    print(f"[CONFIG] Base SQLite  : {sqlite_file}")
    mode_str = "VERIFY (Solo lectura)" if verify_only else ("DRY-RUN (Simulación)" if dry_run else "REAL (Escritura)")
    print(f"[CONFIG] Modo         : {mode_str}")
    print("-" * 70)

    # 1. Cargar SQLite
    try:
        lookup = load_sqlite_chunks(sqlite_file)
    except Exception as exc:
        sys.stderr.write(f"[ERROR] Fallo cargando chunks de SQLite: {exc}\n")
        return 1, {"error": 1}

    print(f"[INFO] Chunks cargados desde SQLite: {len(lookup)}")

    # 2. Conectar a Qdrant
    if client is None:
        try:
            client = get_qdrant_client(url)
        except Exception as exc:
            sys.stderr.write(f"[ERROR] Fallo conectando a Qdrant: {exc}\n")
            return 1, {"error": 1}

    existing_collections = {c.name for c in client.get_collections().collections}
    if collection not in existing_collections:
        sys.stderr.write(f"[ERROR] La colección '{collection}' no existe en Qdrant.\n")
        return 1, {"error": 1}

    # 3. Fase 1: PRE-VALIDACIÓN COMPLETA ANTES DE CUALQUIER ESCRITURA
    print("[INFO] Fase 1: Pre-validando correspondencias de todos los puntos...")
    points_to_update: list[tuple[Any, str, dict[str, Any]]] = []  # (point_id, chunk_id, updates_dict)
    qdrant_chunk_ids: set[str] = set()

    inspected = 0
    already_ok = 0
    inconsistent = 0
    failed = 0
    updated = 0

    for point in scroll_all_points(client, collection):
        inspected += 1
        payload = point.payload or {}
        chunk_id = payload.get("chunk_id")
        p_version_id = payload.get("version_id")
        p_doc_id = payload.get("document_id")

        if not chunk_id:
            print(f"[ERROR] Punto {point.id} carece de 'chunk_id' en payload.")
            inconsistent += 1
            continue

        qdrant_chunk_ids.add(chunk_id)

        # Validar correspondencia con SQLite
        sq_data = lookup.get(chunk_id)
        if sq_data is None:
            print(f"[ERROR] Punto {point.id} (chunk_id='{chunk_id}') es huérfano (no existe en SQLite).")
            inconsistent += 1
            continue

        if p_version_id != sq_data["version_id"]:
            print(
                f"[ERROR] Inconsistencia en chunk_id='{chunk_id}': "
                f"version_id en Qdrant ('{p_version_id}') != SQLite ('{sq_data['version_id']}')"
            )
            inconsistent += 1
            continue

        if p_doc_id and p_doc_id != sq_data["document_id"]:
            print(
                f"[ERROR] Inconsistencia en chunk_id='{chunk_id}': "
                f"document_id en Qdrant ('{p_doc_id}') != SQLite ('{sq_data['document_id']}')"
            )
            inconsistent += 1
            continue

        expected_family = sq_data["family_id"]
        expected_cat = sq_data["categoria_id"]

        # Determinar si requiere actualización de metadatos
        updates: dict[str, Any] = {}
        if payload.get("family_id") != expected_family:
            updates["family_id"] = expected_family
        if payload.get("categoria_id") != expected_cat:
            updates["categoria_id"] = expected_cat

        if updates:
            points_to_update.append((point.id, chunk_id, updates))
        else:
            already_ok += 1

    # Detectar chunks en SQLite sin punto en Qdrant
    sqlite_only = set(lookup.keys()) - qdrant_chunk_ids
    if sqlite_only:
        print(f"[ERROR] {len(sqlite_only)} chunk(s) en SQLite no tienen punto en Qdrant:")
        for cid in sorted(sqlite_only)[:10]:
            print(f"        - {cid}")
        if len(sqlite_only) > 10:
            print(f"        ... y {len(sqlite_only) - 10} más.")
        inconsistent += len(sqlite_only)

    pending = len(points_to_update)

    print(f"[INFO] Pre-validación finalizada:")
    print(f"       - Inspeccionados : {inspected}")
    print(f"       - Inconsistentes : {inconsistent}")
    print(f"       - Pendientes     : {pending}")
    print(f"       - Ya correctos   : {already_ok}")

    # Si hay inconsistencias, abortar ANTES de escribir
    if inconsistent > 0:
        print("[ABORT] Se detectaron inconsistencias en las relaciones. Operación abortada sin realizar cambios.")
        stats = {
            "inspected": inspected,
            "pending": pending,
            "already_ok": already_ok,
            "updated": 0,
            "inconsistent": inconsistent,
            "failed": 0,
            "sqlite_only": len(sqlite_only),
        }
        return 1, stats

    # 4. Fase 2: APLICACIÓN O SIMULACIÓN
    if verify_only or dry_run:
        if pending > 0:
            print(f"\n[INFO] {mode_str}: Se actualizarían {pending} punto(s):")
            for pid, cid, upds in points_to_update[:10]:
                print(f"       Punto {pid} (chunk='{cid}'): {upds}")
            if pending > 10:
                print(f"       ... y {pending - 10} punto(s) adicionales.")
        else:
            print(f"\n[OK] {mode_str}: Todos los puntos ({already_ok}) ya tienen los metadatos correctos.")

        stats = {
            "inspected": inspected,
            "pending": pending,
            "already_ok": already_ok,
            "updated": 0,
            "inconsistent": 0,
            "failed": 0,
            "sqlite_only": len(sqlite_only),
        }
        print("\n" + "=" * 70)
        print("RESUMEN DE MIGRACIÓN")
        print("=" * 70)
        for k, v in stats.items():
            print(f"  {k:<15}: {v}")
        print("=" * 70)
        return 0, stats

    # MODO ESCRITURA REAL
    print(f"\n[INFO] Aplicando actualizaciones sobre {pending} punto(s)...")
    for pid, cid, upds in points_to_update:
        try:
            client.set_payload(
                collection_name=collection,
                payload=upds,
                points=[pid],
                wait=True,
            )
            updated += 1
        except Exception as exc:
            print(f"[ERROR] Error al actualizar payload del punto {pid} (chunk='{cid}'): {exc}")
            failed += 1

    stats = {
        "inspected": inspected,
        "pending": pending,
        "already_ok": already_ok,
        "updated": updated,
        "inconsistent": inconsistent,
        "failed": failed,
        "sqlite_only": len(sqlite_only),
    }

    print("\n" + "=" * 70)
    print("RESUMEN DE MIGRACIÓN")
    print("=" * 70)
    for k, v in stats.items():
        print(f"  {k:<15}: {v}")
    print("=" * 70)

    if failed > 0:
        print("[RESULTADO] Migración finalizada con ERRORES de actualización.")
        return 1, stats

    print("[RESULTADO] Migración completada exitosamente.")
    return 0, stats


# ---------------------------------------------------------------------------
# Entrada CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Migración idempotente de payloads en Qdrant (family_id + categoria_id)."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simula la migración y contabiliza las actualizaciones previstas sin escribir.",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Modo de solo lectura: comprueba coherencia sin aplicar cambios.",
    )
    parser.add_argument("--url", help="URL de Qdrant (override de settings.QDRANT_URL)")
    parser.add_argument("--collection", help="Nombre de colección Qdrant (override de settings.QDRANT_COLLECTION)")
    parser.add_argument("--db-path", help="Ruta a base SQLite (override de settings.SQLITE_PATH)")

    args = parser.parse_args()

    if args.dry_run and args.verify:
        sys.stderr.write("[ERROR] Las opciones --dry-run y --verify son mutuamente excluyentes.\n")
        return 2

    exit_code, _ = run_migration(
        qdrant_url=args.url,
        collection_name=args.collection,
        db_path=args.db_path,
        dry_run=args.dry_run,
        verify_only=args.verify,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
