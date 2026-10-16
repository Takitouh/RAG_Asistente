from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from normativa.ingestion.extractor import extract_pages, should_use_text_layer


def _create_text_pdf(path: Path, text: str) -> None:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica", 14)
    c.drawString(72, A4[1] - 72, text)
    c.showPage()
    c.save()


def _create_image_pdf(path: Path, text: str) -> None:
    image_path = path.with_suffix(".png")
    image = Image.new("RGB", (1800, 500), "white")
    draw = ImageDraw.Draw(image)
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    font = ImageFont.truetype(str(font_path), 96) if font_path.exists() else ImageFont.load_default()
    draw.text((80, 180), text, fill="black", font=font)
    image.save(image_path)

    c = canvas.Canvas(str(path), pagesize=A4)
    c.drawImage(str(image_path), 0, 0, width=A4[0], height=A4[1])
    c.showPage()
    c.save()


def _tesseract_ready() -> bool:
    if subprocess.run(["bash", "-lc", "command -v tesseract >/dev/null 2>&1"], check=False).returncode != 0:
        return False
    completed = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, check=False)
    return "spa" in completed.stdout.splitlines()


def test_should_use_text_layer_decision() -> None:
    assert should_use_text_layer("hola mundo", min_chars=5, force_ocr=False)
    assert not should_use_text_layer("hola", min_chars=5, force_ocr=False)
    assert not should_use_text_layer("hola mundo", min_chars=5, force_ocr=True)


def test_extract_pages_prefers_text_layer(tmp_path: Path) -> None:
    pdf_path = tmp_path / "text_layer.pdf"
    _create_text_pdf(pdf_path, "Este documento tiene capa de texto")

    pages = extract_pages(pdf_path, min_chars=1)

    assert len(pages) == 1
    assert pages[0].method == "text_layer"
    assert "capa de texto" in pages[0].text
    assert pages[0].lines


@pytest.mark.skipif(not _tesseract_ready(), reason="tesseract with spa language not available")
def test_extract_pages_uses_ocr_for_scanned_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    _create_image_pdf(pdf_path, "Hola mundo")

    pages = extract_pages(pdf_path, min_chars=1000, force_ocr=False)

    assert len(pages) == 1
    assert pages[0].method == "ocr"
    assert pages[0].text.strip()
    assert pages[0].ocr_confidence is None or pages[0].ocr_confidence >= 0

