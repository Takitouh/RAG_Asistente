#!/usr/bin/env python3
"""scripts/etapa2/cargar_e_indexar_corpus_etapa2.py

Carga, segmentación, persistencia en SQLite e indexación en Qdrant
de todos los documentos del corpus documental para la Etapa 2.

Garantiza:
1. Conservación estricta de versiones históricas (uts_tg_2019 se mantiene intacto).
2. Los nuevos documentos quedan con is_active = 0 y estado_revision = 'PENDIENTE'.
3. Ningún documento queda automáticamente aprobado ni activado.
4. Correspondencia 1:1 verificada entre chunks de SQLite y puntos en Qdrant.
5. Generación de tabla consolidada por documento y versión.

Uso:
    uv run python scripts/etapa2/cargar_e_indexar_corpus_etapa2.py
"""

from __future__ import annotations

import json
from pathlib import Path

from normativa.corpus import db
from normativa.corpus.service import CorpusService
from normativa.retrieval.indexer import QdrantCorpusIndexer

ROOT = Path(__file__).parent.parent.parent


def main():
    print("=" * 80)
    print("ETAPA 2: Carga, Segmentación e Indexación Real del Corpus en SQLite y Qdrant")
    print("=" * 80)

    service = CorpusService()
    indexer = QdrantCorpusIndexer()

    # Definición de documentos a registrar e indexar
    corpus_docs = [
        # 1. Reglamento 2021 (Acuerdo 01-026)
        {
            "version_id": "uts_tg_2021",
            "pdf_path": ROOT / "documentos_fuente" / "reglamentos" / "reglamento_2021.pdf",
            "nombre": "Reglamento de Trabajo de Grado 2021",
            "family_id": "fam_reglamento_tg",
            "numero_acuerdo": "01-026",
            "anio": 2021,
            "fecha_expedicion": "2021-07-27",
            "procedencia": "Consejo Directivo UTS",
            "estado_vigencia": "Vigente",
            "expected_articles": 74,
        },
        # 2. Procedimiento P-DC-28
        {
            "version_id": "ver_p_dc_28_v3",
            "pdf_path": ROOT / "documentos_fuente" / "procedimientos" / "P-DC-28.pdf",
            "nombre": "P-DC-28 Presentación de la Propuesta de Trabajo de Grado",
            "family_id": "fam_p_dc_28",
            "numero_version_institucional": "3.0",
            "procedencia": "Sistema Integrado de Gestión UTS",
            "estado_vigencia": "Vigente",
            "expected_articles": None,
        },
        # 3. Procedimiento P-DC-29
        {
            "version_id": "ver_p_dc_29_v3",
            "pdf_path": ROOT / "documentos_fuente" / "procedimientos" / "P-DC-29.pdf",
            "nombre": "P-DC-29 Presentación del Informe Final de Trabajo de Grado",
            "family_id": "fam_p_dc_29",
            "numero_version_institucional": "3.0",
            "procedencia": "Sistema Integrado de Gestión UTS",
            "estado_vigencia": "Vigente",
            "expected_articles": None,
        },
        # 4. Formatos Institucionales
        {
            "version_id": "ver_f_am_04_v18",
            "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados" / "F-AM-04 Solicitud Grado V18..pdf",
            "nombre": "F-AM-04 Solicitud de Grado V18",
            "family_id": "fam_f_am_04",
            "numero_version_institucional": "18",
            "procedencia": "Suministrado por Directora de Trabajo de Grado",
            "estado_vigencia": "Plantilla institucional",
            "expected_articles": None,
        },
        {
            "version_id": "ver_f_dc_124_v2",
            "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados" / "F-DC-124 Propuesta trabajo grado  Investigación, Desarrollo Tecnológico, Monografía y Emprendimiento V2.pdf",
            "nombre": "F-DC-124 Propuesta de Trabajo de Grado V2",
            "family_id": "fam_f_dc_124",
            "numero_version_institucional": "2.0",
            "procedencia": "Suministrado por Directora de Trabajo de Grado",
            "estado_vigencia": "Plantilla institucional",
            "expected_articles": None,
        },
        {
            "version_id": "ver_f_dc_125_v2",
            "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados" / "F-DC-125  Informe final trabajo grado modalidad proyecto de investigación, desarrollo tecnológico, monografía, emprendimiento y seminario V2.pdf",
            "nombre": "F-DC-125 Informe Final de Trabajo de Grado V2",
            "family_id": "fam_f_dc_125",
            "numero_version_institucional": "2.0",
            "procedencia": "Suministrado por Directora de Trabajo de Grado",
            "estado_vigencia": "Plantilla institucional",
            "expected_articles": None,
        },
        {
            "version_id": "ver_f_dc_126_v2",
            "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados" / "F-DC-126 Requerimiento de la empresa para solicitar practicantes V2.pdf",
            "nombre": "F-DC-126 Requerimiento de Empresa para Practicantes V2",
            "family_id": "fam_f_dc_126",
            "numero_version_institucional": "2.0",
            "procedencia": "Suministrado por Directora de Trabajo de Grado",
            "estado_vigencia": "Plantilla institucional",
            "expected_articles": None,
        },
        {
            "version_id": "ver_f_dc_127_v2",
            "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados" / "F-DC-127 Propuesta de trabajo de grado_ Modalidad Práctica  V2.pdf",
            "nombre": "F-DC-127 Propuesta Modalidad Práctica V2",
            "family_id": "fam_f_dc_127",
            "numero_version_institucional": "2.0",
            "procedencia": "Suministrado por Directora de Trabajo de Grado",
            "estado_vigencia": "Plantilla institucional",
            "expected_articles": None,
        },
        {
            "version_id": "ver_f_dc_128_v2",
            "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados" / "F-DC-128 Informe final de trabajo de grado en modalidad de práctica V2.pdf",
            "nombre": "F-DC-128 Informe Final Modalidad Práctica V2",
            "family_id": "fam_f_dc_128",
            "numero_version_institucional": "2.0",
            "procedencia": "Suministrado por Directora de Trabajo de Grado",
            "estado_vigencia": "Plantilla institucional",
            "expected_articles": None,
        },
        {
            "version_id": "ver_f_dc_129_v2",
            "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados" / "F-DC-129 Rejilla de evaluación informe final de trabajo de grado V2.pdf",
            "nombre": "F-DC-129 Rejilla de Evaluación Informe Final V2",
            "family_id": "fam_f_dc_129",
            "numero_version_institucional": "2.0",
            "procedencia": "Suministrado por Directora de Trabajo de Grado",
            "estado_vigencia": "Plantilla institucional",
            "expected_articles": None,
        },
        {
            "version_id": "ver_f_dc_130_v4",
            "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados" / "F-DC-130 Concepto final del trabajo de grado V4..pdf",
            "nombre": "F-DC-130 Concepto Final del Trabajo de Grado V4",
            "family_id": "fam_f_dc_130",
            "numero_version_institucional": "4.0",
            "procedencia": "Suministrado por Directora de Trabajo de Grado",
            "estado_vigencia": "Plantilla institucional",
            "expected_articles": None,
        },
        {
            "version_id": "ver_f_dc_196_v2",
            "pdf_path": ROOT / "documentos_fuente" / "formatos" / "pdf_derivados" / "F-DC-196 Acta de Terminación y Recibo a Satisfacción de Prácticas V2.pdf",
            "nombre": "F-DC-196 Acta Terminación y Recibo a Satisfacción V2",
            "family_id": "fam_f_dc_196",
            "numero_version_institucional": "2.0",
            "procedencia": "Suministrado por Directora de Trabajo de Grado",
            "estado_vigencia": "Plantilla institucional",
            "expected_articles": None,
        },
    ]

    for item in corpus_docs:
        vid = item["version_id"]
        pdf_file = item["pdf_path"]
        print(f"\n---> Procesando [{vid}]: {item['nombre']}...")
        if not pdf_file.exists():
            print(f"  [ERROR] No existe el archivo: {pdf_file}")
            continue

        file_bytes = pdf_file.read_bytes()

        # Si ya existe en DB, verificar si ya está indexado
        existing = db.get_version(vid)
        if existing is None:
            doc, ver = service.register_document(
                file_bytes=file_bytes,
                filename=pdf_file.name,
                version_id=vid,
                nombre=item["nombre"],
                family_id=item["family_id"],
                numero_version_institucional=item.get("numero_version_institucional"),
                numero_acuerdo=item.get("numero_acuerdo"),
                anio=item.get("anio"),
                fecha_expedicion=item.get("fecha_expedicion"),
                procedencia=item.get("procedencia"),
                estado_vigencia=item.get("estado_vigencia"),
            )
            print(f"  Registrado en SQLite: {vid}")
        else:
            print(f"  Ya registrado previamente: {vid}")

        # Procesar e indexar en Qdrant
        updated_ver = service.process_and_index_version(
            version_id=vid,
            skip_vector_index=False,
            expected_articles_count=item.get("expected_articles"),
        )

        # Garantizar que permanezca INACTIVO y PENDIENTE de revisión humana
        db.update_version_status(
            version_id=vid,
            status=updated_ver.status,
            estado_revision="PENDIENTE",
            observaciones_revision="Procesado e indexado en Etapa 2. Pendiente de inspección y aprobación humana.",
            chunks_count=updated_ver.chunks_count,
        )
        # Asegurar is_active = 0
        with db.get_connection() as conn:
            conn.execute("UPDATE versions SET is_active = 0 WHERE id = ?", (vid,))

        q_count = indexer.count_version_points(vid)
        print(f"  Resultado: Chunks SQLite={updated_ver.chunks_count} | Puntos Qdrant={q_count} | Status={updated_ver.status.value} | Revisión=PENDIENTE | Activo=0")

    # Resumen final de correspondencia SQLite ↔ Qdrant
    print("\n" + "=" * 80)
    print("VERIFICACIÓN CONSOLIDADA DE CORRESPONDENCIA SQLITE ↔ QDRANT")
    print("=" * 80)

    with db.get_connection() as conn:
        all_versions = conn.execute(
            """
            SELECT v.id, v.nombre, f.codigo as fam_code, f.perfil_procesamiento,
                   d.filename, v.chunks_count, v.status, v.estado_revision,
                   v.is_active, v.estado_vigencia, v.numero_acuerdo, v.anio
            FROM versions v
            JOIN families f ON v.family_id = f.id
            JOIN documents d ON v.document_id = d.id
            ORDER BY v.created_at
            """
        ).fetchall()

    table_rows = []
    all_match = True

    header = f"{'Código':<12} | {'Nombre':<35} | {'Perfil':<25} | {'Chunks':<6} | {'Qdrant':<6} | {'Status':<16} | {'Revisión':<18} | {'Activo':<6} | {'Vigencia':<16}"
    print(header)
    print("-" * len(header))

    for row in all_versions:
        vid = row["id"]
        qdrant_points = indexer.count_version_points(vid)
        sqlite_chunks = row["chunks_count"]
        coincide = (qdrant_points == sqlite_chunks)
        if not coincide:
            all_match = False

        status_str = row["status"]
        rev_str = row["estado_revision"]
        active_str = "SÍ (1)" if row["is_active"] == 1 else "NO (0)"
        vig_str = row["estado_vigencia"] or "No determ."

        table_rows.append({
            "id": vid,
            "codigo": row["fam_code"],
            "nombre": row["nombre"][:35],
            "perfil": row["perfil_procesamiento"],
            "chunks_sqlite": sqlite_chunks,
            "puntos_qdrant": qdrant_points,
            "status": status_str,
            "revision": rev_str,
            "activo": active_str,
            "vigencia": vig_str,
            "coincide": coincide,
        })

        row_str = f"{row['fam_code']:<12} | {row['nombre'][:35]:<35} | {row['perfil_procesamiento']:<25} | {sqlite_chunks:<6} | {qdrant_points:<6} | {status_str:<16} | {rev_str:<18} | {active_str:<6} | {vig_str:<16}"
        print(row_str)

    print("-" * len(header))
    if all_match:
        print("✓ CORRESPONDENCIA PERFECTA: Todos los documentos tienen exacta correspondencia 1:1 entre SQLite y Qdrant.")
    else:
        print("✗ ADVERTENCIA: Se detectó desincronización en algunas versiones.")


if __name__ == "__main__":
    main()
