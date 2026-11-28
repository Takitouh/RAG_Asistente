"""scripts/convert_word_to_pdf.py

Script para convertir documentos Word institucionales (DOC/DOCX) a PDF con capa de texto,
preservando intactos los archivos originales y registrando trazabilidad forense (hashes SHA-256,
tamaños, páginas y conteo de caracteres extraíbles).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

import pdfplumber


def compute_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def convert_word_files(
    input_dir: Path,
    output_dir: Path,
    manifest_path: Path | None = None,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    word_files = sorted(
        [p for p in input_dir.iterdir() if p.suffix.lower() in {".doc", ".docx"} and not p.name.startswith("~")]
    )

    manifest: list[dict[str, Any]] = []

    for word_path in word_files:
        orig_sha = compute_sha256(word_path)
        orig_size = word_path.stat().st_size

        pdf_name = f"{word_path.stem}.pdf"
        pdf_path = output_dir / pdf_name

        # Convertir con LibreOffice si no existe o ha cambiado
        if not pdf_path.exists():
            print(f"[CONVERT] Convirtiendo '{word_path.name}' a PDF...")
            cmd = [
                "soffice",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_dir),
                str(word_path),
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                print(f"[ERROR] Error al convertir '{word_path.name}': {res.stderr}")
                continue

        if not pdf_path.exists():
            print(f"[ERROR] PDF no generado para '{word_path.name}'")
            continue

        pdf_sha = compute_sha256(pdf_path)
        pdf_size = pdf_path.stat().st_size

        # Verificar capa de texto del PDF derivado
        with pdfplumber.open(pdf_path) as plum:
            page_count = len(plum.pages)
            char_counts = [len(p.extract_text() or "") for p in plum.pages]
            total_chars = sum(char_counts)
            table_counts = sum(len(p.extract_tables() or []) for p in plum.pages)

        # Detectar código institucional
        codigo = "DESCONOCIDO"
        for code_candidate in ["F-AM-04", "F-DC-124", "F-DC-125", "F-DC-126", "F-DC-127", "F-DC-128", "F-DC-129", "F-DC-130", "F-DC-196"]:
            if code_candidate in word_path.name:
                codigo = code_candidate
                break

        record = {
            "codigo": codigo,
            "archivo_original": word_path.name,
            "formato_original": word_path.suffix.upper().replace(".", ""),
            "sha256_original": orig_sha,
            "tamano_original_bytes": orig_size,
            "archivo_pdf_derivado": pdf_path.name,
            "sha256_pdf_derivado": pdf_sha,
            "tamano_pdf_bytes": pdf_size,
            "paginas": page_count,
            "caracteres_extraidos": total_chars,
            "tablas_detectadas": table_counts,
            "estado_conversion": "EXITOSO" if total_chars > 0 else "SIN_TEXTO",
        }
        manifest.append(record)
        print(f"[OK] {codigo} -> {pdf_path.name} ({page_count} págs, {total_chars} chars, {table_counts} tablas)")

    if manifest_path:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[INFO] Manifiesto guardado en '{manifest_path}'")

    return manifest


if __name__ == "__main__":
    base = Path(__file__).resolve().parent.parent
    in_dir = base / "documentos_fuente" / "formatos" / "originales"
    out_dir = base / "documentos_fuente" / "formatos" / "pdf_derivados"
    out_manifest = base / "documentos_fuente" / "formatos" / "manifest_conversion_word_pdf.json"

    convert_word_files(in_dir, out_dir, out_manifest)
