from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import pdfplumber
import pypdfium2 as pdfium
import pytesseract


@dataclass(frozen=True, slots=True)
class LineInfo:
    text: str
    y_top_norm: float
    y_bottom_norm: float


@dataclass(frozen=True, slots=True)
class PageText:
    page_number: int
    text: str
    method: Literal["text_layer", "ocr"]
    ocr_confidence: float | None
    lines: list[LineInfo]


def should_use_text_layer(extracted_text: str | None, min_chars: int, force_ocr: bool) -> bool:
    if force_ocr:
        return False
    return len((extracted_text or "").strip()) >= min_chars


def _normalize(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    ratio = value / total
    if ratio < 0.0:
        return 0.0
    if ratio > 1.0:
        return 1.0
    return ratio


def _extract_text_layer_lines_pdfium(page: pdfium.PdfPage) -> tuple[list[LineInfo], str]:
    tp = page.get_textpage()
    width, height = page.get_size()
    full_text = tp.get_text_range()

    lines: list[LineInfo] = []
    clean_lines_text: list[str] = []
    curr_idx = 0
    total_chars = tp.count_chars()

    for raw_line in full_text.splitlines():
        line_str = raw_line.strip()
        idx_in_full = full_text.find(raw_line, curr_idx)
        if idx_in_full != -1:
            curr_idx = idx_in_full + len(raw_line)
        if not line_str:
            continue

        start_char = idx_in_full if idx_in_full != -1 else 0
        while start_char < curr_idx and start_char < len(full_text) and full_text[start_char].isspace():
            start_char += 1
        end_char = curr_idx - 1
        while end_char > start_char and end_char < len(full_text) and full_text[end_char].isspace():
            end_char -= 1

        b_start = tp.get_charbox(start_char) if start_char < total_chars else (0.0, 0.0, 0.0, 0.0)
        b_end = tp.get_charbox(end_char) if end_char < total_chars else b_start

        left = min(b_start[0], b_end[0])
        bottom = min(b_start[1], b_end[1])
        right = max(b_start[2], b_end[2])
        top = max(b_start[3], b_end[3])

        # Exclusión de texto vertical o ubicado en margen derecho institucional (supervisión MEN)
        if (left > width * 0.91 and right > width * 0.94) or "VIGILADO" in line_str or "Ministerio de Educación" in line_str:
            continue

        # Limpieza de caracteres de corte de palabra / guiones suaves de Word/LibreOffice
        line_str = line_str.replace("\ufffe", "").replace("\xad", "").strip()
        if not line_str:
            continue

        y_top_norm = _normalize(height - top, height)
        y_bottom_norm = _normalize(height - bottom, height)

        lines.append(
            LineInfo(
                text=line_str,
                y_top_norm=y_top_norm,
                y_bottom_norm=y_bottom_norm,
            )
        )
        clean_lines_text.append(line_str)

    return lines, "\n".join(clean_lines_text)


def _extract_text_layer_lines(page: pdfplumber.page.Page) -> list[LineInfo]:
    lines = page.extract_text_lines(strip=True, return_chars=False) or []
    page_height = float(page.height or 1.0)
    extracted: list[LineInfo] = []
    for line in lines:
        text = str(line.get("text", "")).strip()
        if not text:
            continue
        top = float(line.get("top", 0.0))
        bottom = float(line.get("bottom", top + float(line.get("height", 0.0))))
        extracted.append(
            LineInfo(
                text=text,
                y_top_norm=_normalize(top, page_height),
                y_bottom_norm=_normalize(bottom, page_height),
            )
        )
    return extracted


def _ocr_lines_from_data(data: dict[str, list], image_height: int) -> tuple[list[LineInfo], str, float | None]:
    grouped: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    texts = data.get("text", [])
    for index, text in enumerate(texts):
        if str(text).strip():
            grouped[
                (
                    int(data["block_num"][index]),
                    int(data["par_num"][index]),
                    int(data["line_num"][index]),
                )
            ].append(index)

    lines: list[LineInfo] = []
    text_lines: list[str] = []
    confidences: list[float] = []

    for key in sorted(grouped):
        indexes = grouped[key]
        ordered = sorted(indexes, key=lambda idx: float(data["left"][idx]))
        words = [str(data["text"][idx]).strip() for idx in ordered if str(data["text"][idx]).strip()]
        if not words:
            continue

        tops = [float(data["top"][idx]) for idx in ordered]
        bottoms = [float(data["top"][idx]) + float(data["height"][idx]) for idx in ordered]
        line_conf = [float(data["conf"][idx]) for idx in ordered if float(data["conf"][idx]) != -1]
        if line_conf:
            confidences.extend(line_conf)

        text = " ".join(words)
        text_lines.append(text)
        lines.append(
            LineInfo(
                text=text,
                y_top_norm=_normalize(min(tops), float(image_height)),
                y_bottom_norm=_normalize(max(bottoms), float(image_height)),
            )
        )

    confidence = sum(confidences) / len(confidences) if confidences else None
    return lines, "\n".join(text_lines), confidence


def _ocr_page(page: pdfium.PdfPage, ocr_dpi: int) -> tuple[list[LineInfo], str, float | None]:
    scale = ocr_dpi / 72.0
    image = page.render(scale=scale).to_pil()
    try:
        data = pytesseract.image_to_data(
            image,
            lang="spa",
            config="--psm 6",
            output_type=pytesseract.Output.DICT,
        )
        return _ocr_lines_from_data(data, image.height)
    finally:
        if hasattr(image, "close"):
            image.close()


def extract_pages(pdf_path: Path, min_chars: int = 50, ocr_dpi: int = 300, force_ocr: bool = False) -> list[PageText]:
    results: list[PageText] = []
    pdfium_doc = pdfium.PdfDocument(str(pdf_path))
    try:
        total_pages = len(pdfium_doc)
        for index in range(1, total_pages + 1):
            pdfium_page = pdfium_doc[index - 1]
            try:
                lines, text_layer_text = _extract_text_layer_lines_pdfium(pdfium_page)
            except Exception as exc:  # noqa: BLE001
                print(f"Página {index}/{total_pages} [text_layer] ERROR: {exc}")
                text_layer_text = ""
                lines = []

            if should_use_text_layer(text_layer_text, min_chars=min_chars, force_ocr=force_ocr):
                print(f"Página {index}/{total_pages} [text_layer] ...")
                results.append(
                    PageText(
                        page_number=index,
                        text=text_layer_text,
                        method="text_layer",
                        ocr_confidence=None,
                        lines=lines,
                    )
                )
                continue

            try:
                lines, text, confidence = _ocr_page(pdfium_page, ocr_dpi)
                print(f"Página {index}/{total_pages} [ocr] ...")
                results.append(
                    PageText(
                        page_number=index,
                        text=text,
                        method="ocr",
                        ocr_confidence=confidence,
                        lines=lines,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                print(f"Página {index}/{total_pages} [ocr] ERROR: {exc}")
                results.append(
                    PageText(
                        page_number=index,
                        text="",
                        method="ocr",
                        ocr_confidence=None,
                        lines=[],
                    )
                )
    finally:
        pdfium_doc.close()
    return results


def pages_to_json(pages: list[PageText], path: Path) -> Path:
    payload = {"pages": [asdict(page) for page in pages]}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def pages_from_json(path: Path) -> list[PageText]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    pages: list[PageText] = []
    for item in payload.get("pages", []):
        lines = [LineInfo(**line) for line in item.get("lines", [])]
        pages.append(
            PageText(
                page_number=int(item["page_number"]),
                text=str(item["text"]),
                method=item["method"],
                ocr_confidence=item.get("ocr_confidence"),
                lines=lines,
            )
        )
    return pages
