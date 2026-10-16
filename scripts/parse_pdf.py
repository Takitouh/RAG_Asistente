from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from normativa.ingestion.cleaner import clean_pages, render_cleaning_log
from normativa.ingestion.extractor import extract_pages, pages_from_json, pages_to_json
from normativa.ingestion.parser import parse_document, render_parse_report, render_parsed_preview


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("--no-cache", action="store_true")
    return parser


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv[1:])
    pdf_path = args.pdf_path
    if not pdf_path.exists():
        raise SystemExit(f"No existe el archivo: {pdf_path}")

    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    cache_path = processed_dir / f"{pdf_path.stem}_pages.json"

    if cache_path.exists() and not args.no_cache:
        pages = pages_from_json(cache_path)
    else:
        pages = extract_pages(pdf_path)
        pages_to_json(pages, cache_path)

    clean_pages_result, cleaning_log = clean_pages(pages)
    parsed = parse_document(clean_pages_result, source_file=str(pdf_path))

    cleaning_log_path = processed_dir / f"{pdf_path.stem}_cleaning_log.txt"
    parsed_json_path = processed_dir / f"{pdf_path.stem}_parsed.json"
    parsed_preview_path = processed_dir / f"{pdf_path.stem}_parsed_preview.md"
    parse_report_path = processed_dir / f"{pdf_path.stem}_parse_report.txt"

    cleaning_log_path.write_text(render_cleaning_log(cleaning_log), encoding="utf-8")
    parsed_json_path.write_text(json.dumps(asdict(parsed), ensure_ascii=False, indent=2), encoding="utf-8")
    parsed_preview_path.write_text(render_parsed_preview(parsed), encoding="utf-8")
    parse_report_path.write_text(render_parse_report(parsed), encoding="utf-8")

    print(cleaning_log_path)
    print(parsed_json_path)
    print(parsed_preview_path)
    print(parse_report_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv))
