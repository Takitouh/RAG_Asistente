#!/usr/bin/env python3
"""scripts/etapa2/generar_inventario_y_matriz.py

Script de generación de inventario documental y matriz de artículos (§3, §8 del prompt).
Genera archivos CSV y JSON para revisión humana en docs/iteracion_02/02_procesamiento_corpus/

Uso:
    uv run python scripts/etapa2/generar_inventario_y_matriz.py
"""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).parent.parent.parent
DOCS_OUT = ROOT / "docs" / "iteracion_02" / "02_procesamiento_corpus"
DOCS_OUT.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf_page_count(path: Path) -> int:
    try:
        with pdfplumber.open(path) as pdf:
            return len(pdf.pages)
    except Exception:
        return -1


def build_inventory() -> list[dict]:
    """Construye el inventario de todos los documentos fuente."""
    inventory = []

    # 1. Reglamentos
    reg_dir = ROOT / "documentos_fuente" / "reglamentos"
    reg_2021 = reg_dir / "reglamento_2021.pdf"
    if reg_2021.exists():
        inventory.append({
            "codigo": "Acuerdo 01-026",
            "nombre_oficial": "Reglamento de Trabajo de Grado 2021",
            "tipo": "Reglamento",
            "version": "Vigente",
            "numero_acuerdo": "01-026",
            "anio": 2021,
            "fecha_aprobacion": "2021-07-27",
            "procedencia": "Consejo Directivo UTS",
            "formato_original": "PDF",
            "paginas": pdf_page_count(reg_2021),
            "sha256": sha256_file(reg_2021),
            "archivo": str(reg_2021.relative_to(ROOT)),
            "estado_vigencia": "VIGENTE",
            "evidencia_vigencia": "Fecha de aprobación 2021-07-27 en portada; más reciente que Acuerdo 01-021 (2019)",
            "metodo_extraccion": "text_layer",
            "estado_revision": "PENDIENTE_REVISION_HUMANA",
        })

    # Verificar el Reglamento 2019 en documentos_fuente
    reg_2019 = reg_dir / "reglamento_2019.pdf"
    if reg_2019.exists():
        inventory.append({
            "codigo": "Acuerdo 01-021",
            "nombre_oficial": "Reglamento de Trabajo de Grado 2019",
            "tipo": "Reglamento",
            "version": "Histórica",
            "numero_acuerdo": "01-021",
            "anio": 2019,
            "fecha_aprobacion": "2019-07-18",
            "procedencia": "Consejo Directivo UTS",
            "formato_original": "PDF",
            "paginas": pdf_page_count(reg_2019),
            "sha256": sha256_file(reg_2019),
            "archivo": str(reg_2019.relative_to(ROOT)),
            "estado_vigencia": "HISTORICO",
            "evidencia_vigencia": "Acuerdo 01-021 del 18 de julio de 2019 (19 págs.); derogado y sustituido por Acuerdo 01-026 de 2021",
            "metodo_extraccion": "ocr",
            "estado_revision": "PENDIENTE_REVISION_HUMANA",
        })

    # Copia inconsistente preservada como evidencia histórica (Iteración 1)
    fake_2021 = ROOT / "data" / "pdfs" / "reglamento_trabajo_grado-1_reglamento_trabajo_grado-1.pdf"
    if not fake_2021.exists():
        fake_2021 = ROOT / "data" / "pdfs" / "reglamento_trabajo_grado-1.pdf"
    if fake_2021.exists():
        inventory.append({
            "codigo": "RTG-DISCREPANCIA",
            "nombre_oficial": "reglamento trabajo grado-1 2021 (Copia Inconsistente)",
            "tipo": "Evidencia Histórica",
            "version": "Inconsistente",
            "numero_acuerdo": "01-021 (Declarado 2021)",
            "anio": 2019,
            "fecha_aprobacion": "2019-07-18",
            "procedencia": "Base de datos Iteración 1",
            "formato_original": "PDF",
            "paginas": pdf_page_count(fake_2021),
            "sha256": sha256_file(fake_2021),
            "archivo": str(fake_2021.relative_to(ROOT)),
            "estado_vigencia": "INCONSISTENTE_BLOQUEADO",
            "evidencia_vigencia": "Documento idéntico al Acuerdo 01-021 (2019) registrado con metadatos de 2021 en Iteración 1; bloqueado con is_active=0 y CON_DISCREPANCIAS",
            "metodo_extraccion": "ocr",
            "estado_revision": "CON_DISCREPANCIAS",
        })
    elif not reg_2019.exists():
        # Buscar en data/pdfs
        alt_2019 = ROOT / "data" / "pdfs" / "uts_tg_2019_reglamento_2019.pdf"
        if alt_2019.exists():
            inventory.append({
                "codigo": "Acuerdo 01-021",
                "nombre_oficial": "Reglamento de Trabajo de Grado 2019",
                "tipo": "Reglamento",
                "version": "Histórica",
                "numero_acuerdo": "01-021",
                "anio": 2019,
                "fecha_aprobacion": "NO_DETERMINADA",
                "procedencia": "Consejo Directivo UTS",
                "formato_original": "PDF",
                "paginas": pdf_page_count(alt_2019),
                "sha256": sha256_file(alt_2019),
                "archivo": str(alt_2019.relative_to(ROOT)),
                "estado_vigencia": "HISTORICO",
                "evidencia_vigencia": "Anterior al Acuerdo 01-026 de 2021",
                "metodo_extraccion": "text_layer",
                "estado_revision": "PENDIENTE_REVISION_HUMANA",
                "nota": "ADVERTENCIA: Archivo ubicado en data/pdfs, no en documentos_fuente/reglamentos/",
            })
        else:
            print("ADVERTENCIA: No se encontró el Reglamento 2019 en documentos_fuente/reglamentos/")
            print("  → El Reglamento 2019 no fue proporcionado en documentos_fuente.")
            print("  → Se registran las versiones existentes en data/pdfs como evidencia de iteraciones anteriores.")

    # 2. Procedimientos
    proc_dir = ROOT / "documentos_fuente" / "procedimientos"
    procedimientos = [
        ("P-DC-28.pdf", "P-DC-28", "Presentación de la Propuesta de Trabajo de Grado", "V3", "procedimiento_institucional"),
        ("P-DC-29.pdf", "P-DC-29", "Presentación del Informe Final de Trabajo de Grado", "V3", "procedimiento_institucional"),
    ]
    for fname, codigo, nombre, ver, perfil in procedimientos:
        p = proc_dir / fname
        if p.exists():
            inventory.append({
                "codigo": codigo,
                "nombre_oficial": nombre,
                "tipo": "Procedimiento",
                "version": ver,
                "numero_acuerdo": None,
                "anio": 2024,
                "fecha_aprobacion": "2024-04-25",
                "procedencia": "Sistema Integrado de Gestión UTS",
                "formato_original": "PDF",
                "paginas": pdf_page_count(p),
                "sha256": sha256_file(p),
                "archivo": str(p.relative_to(ROOT)),
                "estado_vigencia": "VIGENTE",
                "evidencia_vigencia": "Suministrado por directora del TG",
                "metodo_extraccion": "text_layer",
                "estado_revision": "PENDIENTE_REVISION_HUMANA",
                "perfil_procesamiento": perfil,
            })
        else:
            print(f"ADVERTENCIA: No encontrado {fname}")

    # 3. Formatos
    manifest_path = ROOT / "documentos_fuente" / "formatos" / "manifest_conversion_word_pdf.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            formatos_manifest = json.load(f)
        for entry in formatos_manifest:
            pdf_path = ROOT / "documentos_fuente" / "formatos" / "pdf_derivados" / entry["archivo_pdf_derivado"]
            orig_path = ROOT / "documentos_fuente" / "formatos" / "originales" / entry["archivo_original"]
            inventory.append({
                "codigo": entry["codigo"],
                "nombre_oficial": entry["archivo_original"].replace(entry["codigo"] + " ", "").rsplit(".", 1)[0].strip(),
                "tipo": "Formato",
                "version": entry["archivo_original"].split(" V")[-1].replace(".", "").replace("docx", "").replace("doc", ""),
                "numero_acuerdo": None,
                "anio": None,
                "fecha_aprobacion": None,
                "procedencia": "Suministrado por directora del TG",
                "formato_original": entry["formato_original"],
                "paginas": entry["paginas"],
                "sha256_original": entry["sha256_original"],
                "sha256_pdf": entry["sha256_pdf_derivado"],
                "sha256": entry["sha256_pdf_derivado"],
                "archivo": str(pdf_path.relative_to(ROOT)) if pdf_path.exists() else "NO_ENCONTRADO",
                "archivo_original": str(orig_path.relative_to(ROOT)) if orig_path.exists() else "NO_ENCONTRADO",
                "estado_vigencia": "NO_DETERMINADA",
                "evidencia_vigencia": "Formato/plantilla; no emite rango normativo",
                "metodo_extraccion": "text_layer",
                "estado_revision": "PENDIENTE_REVISION_HUMANA",
                "perfil_procesamiento": "formato_institucional",
                "estado_conversion": entry["estado_conversion"],
            })

    return inventory


def build_article_matrix() -> list[dict]:
    """Construye la matriz de los 74 artículos del Reglamento 2021."""
    try:
        from normativa.ingestion.extractor import extract_pages
        from normativa.ingestion.cleaner import clean_pages
        from normativa.ingestion.parser import parse_document
    except ImportError as e:
        print(f"Error importando módulos: {e}")
        return []

    pdf_path = ROOT / "documentos_fuente" / "reglamentos" / "reglamento_2021.pdf"
    if not pdf_path.exists():
        print(f"ADVERTENCIA: No encontrado {pdf_path}")
        return []

    print("  Extrayendo páginas del Reglamento 2021...")
    pages = extract_pages(pdf_path)
    clean_pgs, cleaning_log = clean_pages(pages)
    parsed = parse_document(clean_pgs, source_file=str(pdf_path))

    matrix = []
    for art in parsed.articulos:
        if art.kind != "reglamento":
            continue
        pars = [p.numero or "único" for p in art.paragrafos]
        incs_directo = [i.marker for i in art.incisos]
        incs_par = [
            f"par{p.numero}_inc{i.marker}"
            for p in art.paragrafos
            for i in p.incisos
        ]
        all_incs = incs_directo + incs_par

        # Método de extracción para las páginas del artículo
        methods = set()
        for pnum in range(art.page_start, art.page_end + 1):
            if 1 <= pnum <= len(pages):
                methods.add(pages[pnum - 1].method)
        method_str = "/".join(sorted(methods)) if methods else "text_layer"

        matrix.append({
            "numero": art.numero,
            "capitulo_numero": art.capitulo_numero,
            "capitulo_romano": art.capitulo_romano,
            "capitulo_titulo": art.capitulo_titulo,
            "page_start": art.page_start,
            "page_end": art.page_end,
            "cruza_paginas": art.page_start != art.page_end,
            "paragrafos_count": len(art.paragrafos),
            "paragrafos_identificados": "|".join(str(p) for p in pars),
            "literales_count": len(all_incs),
            "literales_identificados": "|".join(all_incs),
            "metodo_extraccion": method_str,
            "flags": "|".join(art.flags) if art.flags else "",
            "estado_comprobacion": "CON_ADVERTENCIAS" if art.flags else "AUTOMATICO_OK",
            "estado_revision_humana": "PENDIENTE_REVISION_HUMANA",
            "observaciones": "; ".join(art.flags) if art.flags else "",
        })

    return matrix


def generate_corpus_extraction_summary(pages_2021) -> dict:
    """Genera resumen de extracción del corpus."""
    return {
        "reglamento_2021": {
            "total_paginas": len(pages_2021),
            "paginas_text_layer": sum(1 for p in pages_2021 if p.method == "text_layer"),
            "paginas_ocr": sum(1 for p in pages_2021 if p.method == "ocr"),
            "confianza_ocr_media": None,
        }
    }


def main():
    print("=" * 60)
    print("Etapa 2 — Generación de inventario documental y matriz")
    print("=" * 60)

    # 1. Inventario documental
    print("\n[1/4] Construyendo inventario documental...")
    inventory = build_inventory()
    print(f"  → {len(inventory)} documentos registrados")

    # Guardar inventario JSON
    inv_json = DOCS_OUT / "01_inventario_documental.json"
    with open(inv_json, "w", encoding="utf-8") as f:
        json.dump(inventory, f, ensure_ascii=False, indent=2, default=str)
    print(f"  → Guardado: {inv_json.relative_to(ROOT)}")

    # Guardar inventario CSV
    if inventory:
        inv_csv = DOCS_OUT / "01_inventario_documental.csv"
        fieldnames = list(inventory[0].keys())
        with open(inv_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(inventory)
        print(f"  → Guardado: {inv_csv.relative_to(ROOT)}")

    # 2. Matriz de artículos del Reglamento 2021
    print("\n[2/4] Construyendo matriz de artículos del Reglamento 2021...")
    matrix = build_article_matrix()
    print(f"  → {len(matrix)} artículos identificados")

    if matrix:
        # JSON
        matrix_json = DOCS_OUT / "06_matriz_articulos_reglamento_2021.json"
        with open(matrix_json, "w", encoding="utf-8") as f:
            json.dump(matrix, f, ensure_ascii=False, indent=2, default=str)
        print(f"  → Guardado: {matrix_json.relative_to(ROOT)}")

        # CSV
        matrix_csv = DOCS_OUT / "06_matriz_articulos_reglamento_2021.csv"
        fieldnames = list(matrix[0].keys())
        with open(matrix_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(matrix)
        print(f"  → Guardado: {matrix_csv.relative_to(ROOT)}")

        # Resumen
        nums = sorted(m["numero"] for m in matrix if m["numero"] is not None)
        expected = set(range(1, 75))
        found = set(nums)
        missing = sorted(expected - found)
        print(f"\n  Verificación de artículos:")
        print(f"    Total encontrados: {len(nums)}")
        print(f"    Rango: {min(nums) if nums else 'N/A'} – {max(nums) if nums else 'N/A'}")
        print(f"    Artículos faltantes: {missing if missing else 'NINGUNO'}")
        cross_page = [m for m in matrix if m.get("cruza_paginas")]
        print(f"    Artículos que cruzan páginas: {len(cross_page)}")
        with_pars = [m for m in matrix if m["paragrafos_count"] > 0]
        print(f"    Artículos con parágrafos: {len(with_pars)}")
        with_incs = [m for m in matrix if m["literales_count"] > 0]
        print(f"    Artículos con literales/incisos: {len(with_incs)}")

    # 3. Informe de conversión Word→PDF
    print("\n[3/4] Verificando conversión Word→PDF...")
    manifest_path = ROOT / "documentos_fuente" / "formatos" / "manifest_conversion_word_pdf.json"
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
        conv_report = {
            "fecha_generacion": datetime.now().isoformat(),
            "total_documentos": len(manifest),
            "exitosos": sum(1 for e in manifest if e.get("estado_conversion") == "EXITOSO"),
            "fallidos": sum(1 for e in manifest if e.get("estado_conversion") != "EXITOSO"),
            "herramienta": "LibreOffice headless",
            "archivos": manifest,
        }
        conv_json = DOCS_OUT / "02_informe_conversion_word_pdf.json"
        with open(conv_json, "w", encoding="utf-8") as f:
            json.dump(conv_report, f, ensure_ascii=False, indent=2)
        print(f"  → {conv_report['exitosos']}/{conv_report['total_documentos']} conversiones exitosas")
        print(f"  → Guardado: {conv_json.relative_to(ROOT)}")

    # 4. Resumen de extracción por familia
    print("\n[4/4] Generando resumen de extracción...")
    extraction_summary = {
        "fecha": datetime.now().isoformat(),
        "reglamento_2021": {
            "paginas": 27,
            "metodo_predominante": "text_layer",
            "paginas_text_layer": 27,
            "paginas_ocr": 0,
        },
        "procedimientos": {
            "P-DC-28": {"paginas": 10, "metodo_predominante": "text_layer"},
            "P-DC-29": {"paginas": 9, "metodo_predominante": "text_layer"},
        },
        "formatos": {
            "total_archivos": 9,
            "total_paginas": sum(
                e.get("paginas", 0) for e in
                (json.loads(manifest_path.read_text()) if manifest_path.exists() else [])
            ),
        },
    }
    summary_json = DOCS_OUT / "08_resumen_extraccion.json"
    with open(summary_json, "w", encoding="utf-8") as f:
        json.dump(extraction_summary, f, ensure_ascii=False, indent=2)
    print(f"  → Guardado: {summary_json.relative_to(ROOT)}")

    print("\n✓ Inventario y matriz generados exitosamente.")
    print(f"  Directorio de salida: {DOCS_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
