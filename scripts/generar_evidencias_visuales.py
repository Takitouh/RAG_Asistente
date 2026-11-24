#!/usr/bin/env python3
"""Generador de evidencias documentales, vectoriales y de trazabilidad para NORMATIVA-TG UTS."""
import json
import sqlite3
from pathlib import Path
import pypdfium2 as pdfium

EVIDENCIAS_DIR = Path("docs/entrega_final/evidencias")
EVIDENCIAS_DIR.mkdir(parents=True, exist_ok=True)
PDF_PATH = Path("data/pdfs/uts_tg_2019_reglamento_trabajo_grado.pdf")

print("1. Renderizando folios clave del PDF oficial...")
if PDF_PATH.exists():
    pdf = pdfium.PdfDocument(PDF_PATH)
    # Páginas clave (índice 0-based):
    # pág 1 (índice 0): Preámbulo Acuerdo 01-021
    # pág 3 (índice 2): Art. 1 adoptado
    # pág 4 (índice 3): Art. 8 Modalidades
    # pág 5 (índice 4): Art. 11 Equipos y Art. 14 Período 180 días
    # pág 6 (índice 5): Art. 15 Prórrogas y Excepciones
    # pág 11 (índice 10): Art. 30 y 31 Evaluación (Aplazado, Aprobado, Reprobado)
    paginas_a_renderizar = [
        (1, "pdf_pagina_01_acuerdo_preambulo.png"),
        (3, "pdf_pagina_03_art1_reparado.png"),
        (4, "pdf_pagina_04_modalidades_art8.png"),
        (5, "pdf_pagina_05_periodos_art14_grupos_art11.png"),
        (6, "pdf_pagina_06_prorrogas_excepciones_art15.png"),
        (11, "pdf_pagina_11_evaluacion_informe_art31.png"),
    ]
    for num_pag, nombre_salida in paginas_a_renderizar:
        page = pdf.get_page(num_pag - 1)
        # Renderizado a 150 DPI para vista de evidencia visual óptima
        bitmap = page.render(scale=150/72)
        pil_image = bitmap.to_pil()
        out_file = EVIDENCIAS_DIR / nombre_salida
        pil_image.save(out_file)
        print(f"   [OK] {nombre_salida} generado ({pil_image.width}x{pil_image.height} px)")

print("2. Exportando evidencia de trazabilidad en SQLite...")
db_path = Path("data/db/normativa.db")
if db_path.exists():
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    traces = c.execute("SELECT id, created_at, version_id, query, response, abstained, latency_ms FROM traces ORDER BY created_at DESC LIMIT 10").fetchall()
    traces_data = [dict(t) for t in traces]
    (EVIDENCIAS_DIR / "evidencia_ultimas_10_trazas.json").write_text(json.dumps(traces_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"   [OK] evidencia_ultimas_10_trazas.json guardado ({len(traces_data)} registros).")
    conn.close()

print("¡Evidencias generadas exitosamente!")
