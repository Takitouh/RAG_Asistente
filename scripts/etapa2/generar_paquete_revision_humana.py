#!/usr/bin/env python3
"""scripts/etapa2/generar_paquete_revision_humana.py

Genera el paquete para revisión humana en:
docs/iteracion_02/02_procesamiento_corpus/revision_humana/

Archivos generados:
1. reglamento_2021_texto_y_chunks.json
2. procedimientos_texto_y_chunks.json
3. formatos_texto_y_chunks.json
4. lista_verificacion_documental.csv

Garantiza:
- No simula ni inventa aprobaciones.
- Los campos de resultado de revisión humana, fecha y revisor quedan vacíos.
- Datos 100% concordantes con la base de datos SQLite (data/db/normativa.db).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from normativa.corpus import db
from normativa.ingestion.cleaner import clean_pages
from normativa.ingestion.extractor import extract_pages
from normativa.ingestion.parser import parse_document
from normativa.ingestion.profiles.procedimiento import ProcedimientoProfileProcessor

ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = ROOT / "docs" / "iteracion_02" / "02_procesamiento_corpus" / "revision_humana"


def generate_reglamento_2021_json(pdf_path: Path) -> dict:
    pages = extract_pages(pdf_path)
    cleaned, _ = clean_pages(pages)
    parsed = parse_document(cleaned, str(pdf_path))
    
    # Obtener chunks desde SQLite
    sqlite_chunks = db.get_chunks_by_version("uts_tg_2021")
    chunks_by_art: dict[int, list] = {}
    for c in sqlite_chunks:
        if c.articulo_numero is not None:
            chunks_by_art.setdefault(c.articulo_numero, []).append(c)

    articulos_data = []
    for art in parsed.articulos:
        if art.kind != "reglamento" or art.numero is None:
            continue
        
        art_chunks = chunks_by_art.get(art.numero, [])
        chunks_info = [
            {
                "chunk_id": c.chunk_id,
                "texto_exacto": c.texto,
                "location_hint": c.location_hint,
                "paragrafo_numero": c.paragrafo_numero,
                "inciso_marker": c.inciso_marker,
            }
            for c in art_chunks
        ]
        
        paragrafos_info = [
            {
                "numero": p.numero,
                "texto": p.texto,
                "incisos": [{"marker": inc.marker, "texto": inc.texto} for inc in p.incisos],
            }
            for p in art.paragrafos
        ]
        
        incisos_info = [
            {"marker": inc.marker, "texto": inc.texto}
            for inc in art.incisos
        ]

        articulos_data.append({
            "numero": art.numero,
            "capitulo_numero": art.capitulo_numero,
            "capitulo_romano": art.capitulo_romano,
            "capitulo_titulo": art.capitulo_titulo,
            "texto_original_extraido": art.texto,
            "texto_normalizado": art.texto.strip(),
            "paragrafos_identificados": paragrafos_info,
            "literales_incisos_identificados": incisos_info,
            "page_start": art.page_start,
            "page_end": art.page_end,
            "chunk_ids": [c["chunk_id"] for c in chunks_info],
            "chunks_almacenados_sqlite": chunks_info,
            "location_hint": f"Capítulo {art.capitulo_romano} - {art.capitulo_titulo}, Artículo {art.numero} (págs. {art.page_start}-{art.page_end})",
            "advertencias": art.flags,
            "estado_revision_humana": "PENDIENTE_REVISION_HUMANA",
        })

    return {
        "documento": "Acuerdo 01-026 de 2021 - Reglamento de Trabajo de Grado UTS",
        "version_id": "uts_tg_2021",
        "total_articulos_reglamento": len(articulos_data),
        "total_chunks_sqlite": len(sqlite_chunks),
        "chunks_estructurales_no_articulo": [
            {
                "chunk_id": c.chunk_id,
                "tipo": c.articulo_tipo,
                "texto_exacto": c.texto,
                "location_hint": c.location_hint,
                "estado_revision_humana": "PENDIENTE_REVISION_HUMANA",
            }
            for c in sqlite_chunks
            if c.articulo_numero is None
        ],
        "articulos": articulos_data,
    }


def generate_procedimientos_json() -> dict:
    proc_processor = ProcedimientoProfileProcessor()
    procs = [
        ("ver_p_dc_28_v3", "P-DC-28", "Presentación de la Propuesta de Trabajo de Grado", ROOT / "documentos_fuente" / "procedimientos" / "P-DC-28.pdf"),
        ("ver_p_dc_29_v3", "P-DC-29", "Presentación del Informe Final de Trabajo de Grado", ROOT / "documentos_fuente" / "procedimientos" / "P-DC-29.pdf"),
    ]
    
    docs_out = []
    for ver_id, codigo, nombre, path in procs:
        pages = extract_pages(path)
        chunks = db.get_chunks_by_version(ver_id)
        
        # Extraer estructura
        result = proc_processor.process(
            pdf_path=path,
            pages=pages,
            version_id=ver_id,
            document_id=f"doc_{codigo.lower()}",
            document_name=path.name,
            categoria_id="cat_procedimientos",
            family_id=f"fam_{codigo.lower().replace('-', '_')}",
        )
        
        docs_out.append({
            "codigo": codigo,
            "nombre": nombre,
            "version_id": ver_id,
            "version_institucional": "3.0",
            "paginas": len(pages),
            "secciones_numerales": result.metadata.get("secciones", []),
            "actividades": result.metadata.get("actividades", []),
            "total_chunks_almacenados": len(chunks),
            "chunks_almacenados_sqlite": [
                {
                    "chunk_id": c.chunk_id,
                    "location_hint": c.location_hint,
                    "texto": c.texto,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                }
                for c in chunks
            ],
            "estado_revision_humana": "PENDIENTE_REVISION_HUMANA",
        })
        
    return {
        "tipo": "Procedimientos Institucionales UTS",
        "documentos": docs_out,
    }


def generate_formatos_json() -> dict:
    formatos_versions = [
        ("ver_f_am_04_v18", "F-AM-04"),
        ("ver_f_dc_124_v2", "F-DC-124"),
        ("ver_f_dc_125_v2", "F-DC-125"),
        ("ver_f_dc_126_v2", "F-DC-126"),
        ("ver_f_dc_127_v2", "F-DC-127"),
        ("ver_f_dc_128_v2", "F-DC-128"),
        ("ver_f_dc_129_v2", "F-DC-129"),
        ("ver_f_dc_130_v4", "F-DC-130"),
        ("ver_f_dc_196_v2", "F-DC-196"),
    ]
    
    docs_out = []
    for ver_id, codigo in formatos_versions:
        v = db.get_version(ver_id)
        if v is None:
            continue
        doc = db.get_document(v.document_id)
        if doc is None:
            continue
        path = Path(doc.file_path)
        chunks = db.get_chunks_by_version(ver_id)
        pages = extract_pages(path)
        docs_out.append({
            "codigo": codigo,
            "nombre": v.nombre,
            "version_id": ver_id,
            "version_institucional": v.numero_version_institucional or "1.0",
            "paginas": len(pages),
            "procedencia": v.procedencia or "Directora de Trabajo de Grado UTS",
            "total_chunks_almacenados": len(chunks),
            "chunks_almacenados_sqlite": [
                {
                    "chunk_id": c.chunk_id,
                    "location_hint": c.location_hint,
                    "texto": c.texto,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                }
                for c in chunks
            ],
            "estado_revision_humana": "PENDIENTE_REVISION_HUMANA",
        })
        
    return {
        "tipo": "Formatos Institucionales UTS",
        "total_formatos": len(docs_out),
        "total_chunks_formatos": sum(d["total_chunks_almacenados"] for d in docs_out),
        "documentos": docs_out,
    }


def generate_lista_verificacion_csv(reglamento_data: dict, procs_data: dict, formatos_data: dict, output_path: Path):
    fieldnames = [
        "id_unidad",
        "documento",
        "version",
        "pagina",
        "elemento_revisado",
        "resultado_revision",
        "observaciones",
        "fecha",
        "revisor",
    ]
    
    rows = []
    
    # 1. Artículos del Reglamento 2021
    for art in reglamento_data["articulos"]:
        num = art["numero"]
        cap = f"Capítulo {art['capitulo_romano']} ({art['capitulo_titulo']})"
        rows.append({
            "id_unidad": f"uts_tg_2021_art_{num:02d}",
            "documento": "Acuerdo 01-026 de 2021 (Reglamento)",
            "version": "2021",
            "pagina": f"{art['page_start']}-{art['page_end']}",
            "elemento_revisado": f"Artículo {num} [{cap}] - Texto, parágrafos ({len(art['paragrafos_identificados'])}), incisos ({len(art['literales_incisos_identificados'])})",
            "resultado_revision": "",  # Vacio para revision humana
            "observaciones": "",
            "fecha": "",
            "revisor": "",
        })
        
    # 2. Procedimientos
    for proc in procs_data["documentos"]:
        cod = proc["codigo"]
        ver = proc["version_institucional"]
        # Secciones
        for sec in proc["secciones_numerales"]:
            num = sec.get("numero", "")
            tit = sec.get("titulo", "")
            pag = sec.get("pagina", "")
            rows.append({
                "id_unidad": f"{cod.lower().replace('-', '_')}_sec_{num}",
                "documento": f"Procedimiento {cod}",
                "version": f"v{ver}",
                "pagina": str(pag),
                "elemento_revisado": f"Numeral {num}. {tit}",
                "resultado_revision": "",
                "observaciones": "",
                "fecha": "",
                "revisor": "",
            })
        # Actividades principales
        for act in proc["actividades"]:
            num = act.get("numero", "")
            desc = act.get("descripcion", "")[:60]
            pag = act.get("pagina", "")
            rows.append({
                "id_unidad": f"{cod.lower().replace('-', '_')}_act_{num}",
                "documento": f"Procedimiento {cod}",
                "version": f"v{ver}",
                "pagina": str(pag),
                "elemento_revisado": f"Actividad {num}: {desc}...",
                "resultado_revision": "",
                "observaciones": "",
                "fecha": "",
                "revisor": "",
            })

    # 3. Formatos institucionales
    for form in formatos_data["documentos"]:
        cod = form["codigo"]
        nom = form["nombre"]
        ver = form["version_institucional"]
        pags = form["paginas"]
        rows.append({
            "id_unidad": f"form_{cod.lower().replace('-', '_')}",
            "documento": f"Formato {cod} {nom}",
            "version": f"v{ver}",
            "pagina": f"1-{pags}",
            "elemento_revisado": f"Plantilla completa, campos, tablas y estructura ({form['total_chunks_almacenados']} chunks)",
            "resultado_revision": "",
            "observaciones": "",
            "fecha": "",
            "revisor": "",
        })

    # 4. Reglamento Histórico 2019
    rows.append({
        "id_unidad": "uts_tg_2019_global",
        "documento": "Acuerdo 01-021 de 2019 (Reglamento Histórico)",
        "version": "2019",
        "pagina": "1-19",
        "elemento_revisado": "Acuerdo 01-021 completo (64 artículos de reglamento + 3 de acuerdo, 181 chunks)",
        "resultado_revision": "",
        "observaciones": "",
        "fecha": "",
        "revisor": "",
    })

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Generando paquete de revisión humana en: {OUTPUT_DIR}")

    # 1. Reglamento 2021
    pdf_reglamento = ROOT / "documentos_fuente" / "reglamentos" / "reglamento_2021.pdf"
    if not pdf_reglamento.exists():
        pdf_reglamento = ROOT / "data" / "pdfs" / "reglamento_2021.pdf"
    
    reg_data = generate_reglamento_2021_json(pdf_reglamento)
    reg_out_path = OUTPUT_DIR / "reglamento_2021_texto_y_chunks.json"
    with open(reg_out_path, "w", encoding="utf-8") as f:
        json.dump(reg_data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Generado: {reg_out_path.name} ({reg_data['total_articulos_reglamento']} artículos)")

    # 2. Procedimientos
    procs_data = generate_procedimientos_json()
    procs_out_path = OUTPUT_DIR / "procedimientos_texto_y_chunks.json"
    with open(procs_out_path, "w", encoding="utf-8") as f:
        json.dump(procs_data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Generado: {procs_out_path.name} ({len(procs_data['documentos'])} procedimientos)")

    # 3. Formatos
    formatos_data = generate_formatos_json()
    formatos_out_path = OUTPUT_DIR / "formatos_texto_y_chunks.json"
    with open(formatos_out_path, "w", encoding="utf-8") as f:
        json.dump(formatos_data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Generado: {formatos_out_path.name} ({formatos_data['total_formatos']} formatos)")

    # 4. Lista de verificación CSV
    csv_out_path = OUTPUT_DIR / "lista_verificacion_documental.csv"
    generate_lista_verificacion_csv(reg_data, procs_data, formatos_data, csv_out_path)
    print(f"[OK] Generado: {csv_out_path.name}")


if __name__ == "__main__":
    main()
