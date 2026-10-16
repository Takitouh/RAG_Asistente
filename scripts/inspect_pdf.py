from __future__ import annotations

import argparse
import re
import sys
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

from normativa.ingestion.extractor import PageText, extract_pages


HEADER_START_RE = re.compile(r"^(ART[ÍI]CULO|Artículo|Articulo)\b", re.IGNORECASE)
ARTICLE_COUNT_RE = re.compile(r"\barticulo\b", re.IGNORECASE)
CHAPTER_COUNT_RE = re.compile(r"\bcapitulo\b", re.IGNORECASE)
PARAGRAPH_COUNT_RE = re.compile(r"\bparagrafo\b", re.IGNORECASE)
INCISO_RE = re.compile(r"^\s*(?:[a-z]\)|\d+\.)\s+?")


def normalize_for_grouping(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.lower().strip()
    normalized = re.sub(r"\d", "#", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def normalize_for_counts(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.lower()
    normalized = normalized.replace("1", "i").replace("0", "o")
    return normalized


def select_pages(total_pages: int) -> list[int]:
    if total_pages <= 0:
        return []
    middle_start = max(0, (total_pages - 3) // 2)
    indexes = [
        0,
        1,
        2,
        middle_start,
        middle_start + 1,
        middle_start + 2,
        max(0, total_pages - 2),
        max(0, total_pages - 1),
    ]
    seen: set[int] = set()
    ordered: list[int] = []
    for index in indexes:
        if 0 <= index < total_pages and index not in seen:
            seen.add(index)
            ordered.append(index)
    return ordered


def format_page_block(page: PageText) -> str:
    confidence = "—" if page.ocr_confidence is None else f"{page.ocr_confidence:.1f}"
    header = f"=== PÁGINA {page.page_number} [{page.method}, {confidence}] ==="
    body = page.text.rstrip()
    return f"{header}\n{body}".rstrip()


def sample_raw_text(pages: list[PageText]) -> str:
    selected_pages = select_pages(len(pages))
    return "\n".join(format_page_block(pages[index]) for index in selected_pages).rstrip() + "\n"


def full_raw_text(pages: list[PageText]) -> str:
    return "\n".join(format_page_block(page) for page in pages).rstrip() + "\n"


def cluster_header_footer_lines(pages: list[PageText]) -> list[dict[str, object]]:
    clusters: list[dict[str, object]] = []

    for page in pages:
        for line in page.lines:
            normalized = normalize_for_grouping(line.text)
            if not normalized:
                continue

            matched_cluster = None
            for cluster in clusters:
                if SequenceMatcher(None, normalized, cluster["representative"]).ratio() >= 0.85:
                    matched_cluster = cluster
                    break

            if matched_cluster is None:
                matched_cluster = {
                    "representative": normalized,
                    "display": line.text,
                    "pages": set(),
                    "occurrences": [],
                }
                clusters.append(matched_cluster)

            matched_cluster["pages"].add(page.page_number)
            matched_cluster["occurrences"].append(
                {
                    "page": page.page_number,
                    "text": line.text,
                    "y_top": line.y_top_norm,
                    "y_bottom": line.y_bottom_norm,
                }
            )

    return [
        cluster
        for cluster in clusters
        if len(cluster["pages"]) > 0
    ]


def count_patterns(pages: list[PageText]) -> dict[str, int]:
    counts = {
        "CAPÍTULO": 0,
        "ARTÍCULO": 0,
        "PARÁGRAFO": 0,
        "incisos": 0,
    }

    for page in pages:
        text = normalize_for_counts(page.text)
        counts["CAPÍTULO"] += len(CHAPTER_COUNT_RE.findall(text))
        counts["ARTÍCULO"] += len(ARTICLE_COUNT_RE.findall(text))
        counts["PARÁGRAFO"] += len(PARAGRAPH_COUNT_RE.findall(text))
        counts["incisos"] += sum(1 for line in text.splitlines() if INCISO_RE.match(line))

    return counts


def report_text(pages: list[PageText]) -> str:
    total_pages = len(pages)
    lines: list[str] = []
    lines.append(f"Total de páginas: {total_pages}")
    lines.append("Por página:")
    for page in pages:
        confidence = "—" if page.ocr_confidence is None else f"{page.ocr_confidence:.1f}"
        lines.append(
            f"  Página {page.page_number}: método={page.method}, caracteres={len(page.text)}, confianza_ocr={confidence}"
        )

    ocr_confidences = [page.ocr_confidence for page in pages if page.ocr_confidence is not None]
    lines.append("")
    if ocr_confidences:
        average = sum(ocr_confidences) / len(ocr_confidences)
        lines.append(f"Confianza OCR media global: {average:.1f}")
        lines.append("5 páginas con menor confianza:")
        for page in sorted(
            (page for page in pages if page.ocr_confidence is not None),
            key=lambda item: item.ocr_confidence or 0.0,
        )[:5]:
            lines.append(f"  Página {page.page_number}: {page.ocr_confidence:.1f}")
    else:
        lines.append("Confianza OCR media global: —")
        lines.append("5 páginas con menor confianza:")
        lines.append("  Ninguna")

    lines.append("")
    lines.append("Líneas candidatas a encabezado/pie (>40% de las páginas):")
    clusters = cluster_header_footer_lines(pages)
    candidate_clusters = [cluster for cluster in clusters if total_pages and len(cluster["pages"]) / total_pages > 0.4]
    if not candidate_clusters:
        lines.append("  Ninguna")
    else:
        for cluster in sorted(candidate_clusters, key=lambda item: (-len(item["pages"]), item["representative"])):
            occurrences = cluster["occurrences"]
            y_tops = [item["y_top"] for item in occurrences]
            y_bottoms = [item["y_bottom"] for item in occurrences]
            top_hits = sum(1 for item in occurrences if item["y_top"] < 0.15)
            bottom_hits = sum(1 for item in occurrences if item["y_bottom"] > 0.85)
            border_hint = "superior" if top_hits >= bottom_hits and top_hits > 0 else "inferior" if bottom_hits > 0 else "intermedio"
            lines.append(f"  - {cluster['display']}")
            lines.append(f"    Aparece en {len(cluster['pages'])} páginas: {sorted(cluster['pages'])}")
            lines.append(f"    y_top_norm={min(y_tops):.3f}..{max(y_tops):.3f}")
            lines.append(f"    y_bottom_norm={min(y_bottoms):.3f}..{max(y_bottoms):.3f}")
            lines.append(f"    borde probable: {border_hint}")
            for occurrence in sorted(occurrences, key=lambda item: (item["page"], item["y_top"])):
                lines.append(
                    f"    Página {occurrence['page']}: y_top_norm={occurrence['y_top']:.3f}, y_bottom_norm={occurrence['y_bottom']:.3f}, texto={occurrence['text']!r}"
                )

    lines.append("")
    lines.append("Conteo de patrones:")
    pattern_counts = count_patterns(pages)
    lines.append(f"  CAPÍTULO: {pattern_counts['CAPÍTULO']}")
    lines.append(f"  ARTÍCULO: {pattern_counts['ARTÍCULO']}")
    lines.append(f"  PARÁGRAFO: {pattern_counts['PARÁGRAFO']}")
    lines.append(f"  Incisos tipo a)/b)/1.: {pattern_counts['incisos']}")

    lines.append("")
    lines.append("Primeras 40 líneas que empiezan por ARTÍCULO/Artículo:")
    article_lines: list[str] = []
    for page in pages:
        for line in page.text.splitlines():
            if HEADER_START_RE.match(line):
                article_lines.append(f"  PÁGINA {page.page_number}: {line}")
    if not article_lines:
        lines.append("  Ninguna")
    else:
        lines.extend(article_lines[:40])

    return "\n".join(lines).rstrip() + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--force-ocr", action="store_true")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    pdf_path = args.pdf_path
    if not pdf_path.exists():
        print(f"No existe el archivo: {pdf_path}", file=sys.stderr)
        return 1

    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)

    start = time.perf_counter()
    pages = extract_pages(pdf_path, force_ocr=args.force_ocr)
    elapsed = time.perf_counter() - start
    per_page = elapsed / len(pages) if pages else 0.0

    raw_sample_path = output_dir / f"{pdf_path.stem}_raw_sample.txt"
    full_raw_path = output_dir / f"{pdf_path.stem}_full_raw.txt"
    report_path = output_dir / f"{pdf_path.stem}_report.txt"

    raw_sample_path.write_text(sample_raw_text(pages), encoding="utf-8")
    full_raw_path.write_text(full_raw_text(pages), encoding="utf-8")
    report_path.write_text(report_text(pages), encoding="utf-8")

    print(raw_sample_path)
    print(full_raw_path)
    print(report_path)
    print(f"Tiempo total: {elapsed:.2f}s")
    print(f"Tiempo por página: {per_page:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
