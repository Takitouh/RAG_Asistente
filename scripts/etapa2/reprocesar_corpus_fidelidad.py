#!/usr/bin/env python3
"""scripts/etapa2/reprocesar_corpus_fidelidad.py

Reprocesa selectivamente las versiones afectadas por las correcciones de fidelidad:
  - uts_tg_2021: extracción con pypdfium2, literal repetido 'a' en Art. 4, chunks _bis.
  - ver_p_dc_28_v3 y ver_p_dc_29_v3: subnumerales, mejora de sección 7 intro y Numeral 3.
  - Formatos: limpieza \\ufffe/\\xad.

Garantías:
  - uts_tg_2019 y reglamento_trabajo_grado-1 NO se tocan.
  - Ninguna versión pasa a is_active = 1.
  - Se regeneran embeddings SÓLO para chunks cuyo texto cambió.
  - Los vectores no modificados permanecen en Qdrant sin recálculo.
  - Se registran trazas de cada acción.

Uso:
    uv run python scripts/etapa2/reprocesar_corpus_fidelidad.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from normativa.corpus import db
from normativa.corpus.service import CorpusService
from normativa.retrieval.indexer import QdrantCorpusIndexer

ROOT = Path(__file__).resolve().parent.parent.parent

# Versiones que NO deben tocarse bajo ninguna circunstancia
FROZEN_VERSIONS = {"uts_tg_2019", "reglamento_trabajo_grado-1"}

# Versiones a reprocesar en orden
VERSIONS_TO_REPROCESS = [
    {
        "version_id": "uts_tg_2021",
        "pdf_path": ROOT / "documentos_fuente" / "reglamentos" / "reglamento_2021.pdf",
        "expected_articles": 74,
    },
    {
        "version_id": "ver_p_dc_28_v3",
        "pdf_path": ROOT / "documentos_fuente" / "procedimientos" / "P-DC-28.pdf",
        "expected_articles": None,
    },
    {
        "version_id": "ver_p_dc_29_v3",
        "pdf_path": ROOT / "documentos_fuente" / "procedimientos" / "P-DC-29.pdf",
        "expected_articles": None,
    },
    {
        "version_id": "ver_f_am_04_v18",
        "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados" / "F-AM-04 Solicitud Grado V18..pdf",
        "expected_articles": None,
    },
    {
        "version_id": "ver_f_dc_124_v2",
        "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados"
                    / "F-DC-124 Propuesta trabajo grado  Investigación, Desarrollo Tecnológico, Monografía y Emprendimiento V2.pdf",
        "expected_articles": None,
    },
    {
        "version_id": "ver_f_dc_125_v2",
        "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados"
                    / "F-DC-125  Informe final trabajo grado modalidad proyecto de investigación, desarrollo tecnológico, monografía, emprendimiento y seminario V2.pdf",
        "expected_articles": None,
    },
    {
        "version_id": "ver_f_dc_126_v2",
        "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados"
                    / "F-DC-126 Requerimiento de la empresa para solicitar practicantes V2.pdf",
        "expected_articles": None,
    },
    {
        "version_id": "ver_f_dc_127_v2",
        "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados"
                    / "F-DC-127 Propuesta de trabajo de grado_ Modalidad Práctica  V2.pdf",
        "expected_articles": None,
    },
    {
        "version_id": "ver_f_dc_128_v2",
        "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados"
                    / "F-DC-128 Rejilla de Evaluación Propuesta Trabajo de Grado V2.pdf",
        "expected_articles": None,
    },
    {
        "version_id": "ver_f_dc_129_v2",
        "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados"
                    / "F-DC-129 Rejilla de evaluación informe final de trabajo de grado V2.pdf",
        "expected_articles": None,
    },
    {
        "version_id": "ver_f_dc_130_v4",
        "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados"
                    / "F-DC-130 Concepto final del trabajo de grado V4..pdf",
        "expected_articles": None,
    },
    {
        "version_id": "ver_f_dc_196_v2",
        "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados"
                    / "F-DC-196 Acta de Terminación y Recibo a Satisfacción de Prácticas V2.pdf",
        "expected_articles": None,
    },
]


def _text_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def main() -> None:
    print("=" * 80)
    print("REPROCESAMIENTO DE FIDELIDAD DOCUMENTAL - Correcciones de Etapa 2")
    print("=" * 80)

    service = CorpusService()
    indexer = QdrantCorpusIndexer()

    for item in VERSIONS_TO_REPROCESS:
        vid = item["version_id"]
        pdf_path: Path = item["pdf_path"]  # type: ignore[assignment]

        if vid in FROZEN_VERSIONS:
            print(f"\n[IGNORADO] {vid} está en la lista de versiones congeladas.")
            continue

        print(f"\n{'─'*60}")
        print(f"Procesando: {vid}")
        print(f"  PDF: {pdf_path}")

        if not pdf_path.exists():
            print(f"  [ERROR] Archivo no encontrado: {pdf_path}")
            continue

        # Leer chunks anteriores para comparar texto
        old_chunks = db.get_chunks_by_version(vid)
        old_text_by_id: dict[str, str] = {c.chunk_id: c.texto for c in old_chunks}
        old_ids: set[str] = set(old_text_by_id.keys())

        # Reprocesar
        updated_ver = service.process_and_index_version(
            version_id=vid,
            skip_vector_index=False,
            expected_articles_count=item.get("expected_articles"),
        )

        # Garantizar is_active=0, estado_revision sin cambios para los que ya tenían PENDIENTE
        with db.get_connection() as conn:
            conn.execute(
                "UPDATE versions SET is_active = 0 WHERE id = ? AND is_active != 0",
                (vid,),
            )

        # Leer chunks nuevos
        new_chunks = db.get_chunks_by_version(vid)
        new_text_by_id: dict[str, str] = {c.chunk_id: c.texto for c in new_chunks}
        new_ids: set[str] = set(new_text_by_id.keys())

        # Estadísticas de diff
        added = new_ids - old_ids
        removed = old_ids - new_ids
        changed = {
            cid for cid in new_ids & old_ids
            if _text_hash(new_text_by_id[cid]) != _text_hash(old_text_by_id.get(cid, ""))
        }
        unchanged = new_ids & old_ids - changed

        print(f"  Chunks anteriores: {len(old_ids)}")
        print(f"  Chunks nuevos: {len(new_ids)}")
        print(f"  Añadidos: {len(added)} | Eliminados: {len(removed)} | Modificados: {len(changed)} | Sin cambios: {len(unchanged)}")

        q_count = indexer.count_version_points(vid)
        print(f"  SQLite={updated_ver.chunks_count} | Qdrant={q_count} | Coincide={'✓' if updated_ver.chunks_count == q_count else '✗'}")

        if added:
            print(f"  Nuevos chunk IDs: {sorted(added)[:5]}{'...' if len(added)>5 else ''}")
        if removed:
            print(f"  Eliminados chunk IDs: {sorted(removed)[:5]}{'...' if len(removed)>5 else ''}")

    # Verificación final
    print("\n" + "=" * 80)
    print("VERIFICACIÓN FINAL CONSOLIDADA SQLite ↔ Qdrant")
    print("=" * 80)

    with db.get_connection() as conn:
        all_versions = conn.execute(
            """
            SELECT v.id, v.nombre, v.chunks_count, v.is_active, v.estado_revision
            FROM versions v
            ORDER BY v.created_at
            """
        ).fetchall()

    all_ok = True
    print(f"{'ID':<30} | {'Chunks':<7} | {'Qdrant':<7} | {'OK':<3} | {'Activo':<6} | Revisión")
    print("-" * 85)
    for row in all_versions:
        vid = row["id"]
        q = indexer.count_version_points(vid)
        s = row["chunks_count"] or 0
        ok = s == q
        if not ok:
            all_ok = False
        active = "SÍ" if row["is_active"] else "NO"
        rev = row["estado_revision"] or "?"
        flag = "✓" if ok else "✗"
        print(f"{vid:<30} | {s:<7} | {q:<7} | {flag}  | {active:<6} | {rev}")

    print("-" * 85)

    # Verificar que uts_tg_2019 sigue siendo la única versión activa
    with db.get_connection() as conn:
        active_versions = conn.execute(
            "SELECT id FROM versions WHERE is_active = 1"
        ).fetchall()
    active_ids = [r["id"] for r in active_versions]
    if active_ids == ["uts_tg_2019"]:
        print("✓ Versión activa: sólo uts_tg_2019 (correcto)")
    else:
        print(f"✗ ALERTA: Versiones activas inesperadas: {active_ids}")

    if all_ok:
        print("✓ CORRESPONDENCIA PERFECTA 1:1 SQLite ↔ Qdrant en todas las versiones.")
    else:
        print("✗ Se detectó desincronización — revisar manualmente.")


if __name__ == "__main__":
    main()
