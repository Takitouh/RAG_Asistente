from __future__ import annotations

import json
from pathlib import Path

import pytest

from normativa.ingestion.cleaner import CleanLine, CleanPage, clean_pages
from normativa.ingestion.extractor import LineInfo, PageText, pages_from_json
from normativa.ingestion.models import ParsedDocument
from normativa.ingestion.parser import parse_document


def _line(text: str, top: float, bottom: float | None = None) -> LineInfo:
    return LineInfo(text=text, y_top_norm=top, y_bottom_norm=bottom if bottom is not None else top + 0.01)


def _page(number: int, texts: list[tuple[str, float]], conf: float | None = 92.0) -> PageText:
    lines = [_line(text, top) for text, top in texts]
    return PageText(page_number=number, text="\n".join(text for text, _ in texts), method="ocr", ocr_confidence=conf, lines=lines)


def _clean_page(number: int, texts: list[str], conf: float | None = 92.0) -> CleanPage:
    lines = [CleanLine(text=text, y_top_norm=0.1 + index * 0.05, y_bottom_norm=0.11 + index * 0.05) for index, text in enumerate(texts)]
    return CleanPage(page_number=number, ocr_confidence=conf, lines=lines)


def test_article_header_misread_is_repaired_by_sequence() -> None:
    clean = [
        _clean_page(1, ["ARTÍCULO 4. Primer artículo", "ARTÍCULO 2. Segundo artículo", "PUBLÍQUESE"]),
    ]
    parsed = parse_document(clean, "synthetic.pdf")
    assert parsed.articulos[0].numero == 1
    assert "numero_reparado" in parsed.articulos[0].flags


def test_capitalized_reference_does_not_create_article() -> None:
    clean = [
        _clean_page(1, ["Artículo 14, tendrá derecho a continuar.", "ARTÍCULO 1. Texto real", "PUBLÍQUESE"]),
    ]
    parsed = parse_document(clean, "synthetic.pdf")
    assert len(parsed.articulos) == 1
    assert "Artículo 14, tendrá derecho a continuar." in parsed.preambulo


def test_chapter_number_normalization_handles_ocr_variants() -> None:
    clean = [
        _clean_page(1, ["CAPÍTULO |", "TÍTULO UNO", "ARTÍCULO 1. Texto"]),
        _clean_page(2, ["CAPÍTULO Il", "TÍTULO DOS", "ARTÍCULO 2. Texto"]),
        _clean_page(3, ["CAPÍTULO Ill", "TÍTULO TRES", "ARTÍCULO 3. Texto", "PUBLÍQUESE"]),
    ]
    parsed = parse_document(clean, "synthetic.pdf")
    assert [article.capitulo_numero for article in parsed.articulos[:3]] == [1, 2, 3]


def test_inciso_sequence_accepts_ocr_variants() -> None:
    clean = [
        _clean_page(
            1,
            [
                "ARTÍCULO 1. Texto",
                "a. uno",
                "b. dos",
                "Cc. tres",
                "d. cuatro",
                "e. cinco",
                "f.. seis",
                "9. siete",
                "PUBLÍQUESE",
            ],
        )
    ]
    parsed = parse_document(clean, "synthetic.pdf")
    markers = [inc.marker for inc in parsed.articulos[0].incisos]
    assert markers[:7] == ["a", "b", "c", "d", "e", "f", "g"]


def test_paragraph_crossing_pages_is_joined() -> None:
    clean = [
        _clean_page(1, ["ARTÍCULO 1. Texto", "PARÁGRAFO 1. Primera línea del párrafo"]),
        _clean_page(2, ["continúa en la segunda página", "PUBLÍQUESE"]),
    ]
    parsed = parse_document(clean, "synthetic.pdf")
    assert parsed.articulos[0].paragrafos[0].texto.startswith("Primera línea")
    assert "continúa en la segunda página" in parsed.articulos[0].paragrafos[0].texto


def test_footer_noise_is_removed_by_position_and_similarity() -> None:
    pages = [
        _page(1, [("ARTÍCULO 1. Texto", 0.2), ("Footer A", 0.92)]),
        _page(2, [("ARTÍCULO 2. Texto", 0.2), ("Footer B", 0.92)]),
        _page(3, [("ARTÍCULO 3. Texto", 0.2), ("Footer C", 0.92)]),
    ]
    cleaned, log = clean_pages(pages)
    assert all("Footer" not in line.text for page in cleaned for line in page.lines)
    assert any(item.reason == "footer" for item in log.removed_lines)


def test_index_is_removed_but_real_chapter_is_kept() -> None:
    pages = [
        _page(1, [("Índice General", 0.1), ("CAPÍTULO 1 - ALGO", 0.2), ("CAPÍTULO I", 0.3), ("TÍTULO", 0.35)]),
    ]
    cleaned, _ = clean_pages(pages)
    kept_texts = [line.text for page in cleaned for line in page.lines]
    assert "CAPÍTULO 1 - ALGO" not in kept_texts
    assert "CAPÍTULO I" in kept_texts


def test_ordinals_and_publish_split_acuerdo_articles() -> None:
    clean = [
        _clean_page(1, ["ARTÍCULO PRIMERO. Inicio del acuerdo", "ARTÍCULO DOS: Segundo acuerdo", "ARTÍCULO TRES: Tercer acuerdo", "PUBLÍQUESE", "Texto posterior"]),
    ]
    parsed = parse_document(clean, "synthetic.pdf")
    ordinals = [article.ordinal for article in parsed.articulos if article.kind == "acuerdo"]
    assert ordinals == ["PRIMERO", "DOS", "TRES"]
    assert parsed.cierre.startswith("PUBLÍQUESE")


def test_token_cleaning_removes_symbol_tokens() -> None:
    clean = [
        _clean_page(1, ["ARTÍCULO 1. [de texto [Ol", "PUBLÍQUESE"]),
    ]
    parsed = parse_document(clean, "synthetic.pdf")
    assert parsed.articulos[0].texto.startswith("de texto")
    assert "Ol" not in parsed.articulos[0].texto


@pytest.mark.skipif(not Path("data/processed/reglamento_trabajo_grado_pages.json").exists(), reason="reference OCR cache missing")
def test_reference_document_regression() -> None:
    pages = pages_from_json(Path("data/processed/reglamento_trabajo_grado_pages.json"))
    cleaned, log = clean_pages(pages)
    parsed = parse_document(cleaned, "data/pdfs/reglamento_trabajo_grado.pdf")

    reglamento = [article for article in parsed.articulos if article.kind == "reglamento"]
    acuerdos = [article for article in parsed.articulos if article.kind == "acuerdo"]

    assert len(reglamento) == 64
    assert [article.numero for article in reglamento] == list(range(1, 65))
    assert any("numero_reparado" in article.flags for article in reglamento if article.numero == 1)
    chapter_numbers = [article.capitulo_numero for article in reglamento if article.capitulo_numero is not None]
    unique_chapters = []
    for value in chapter_numbers:
        if value not in unique_chapters:
            unique_chapters.append(value)
    assert unique_chapters == list(range(1, 17))
    assert next(article for article in reglamento if article.capitulo_numero == 3).capitulo_titulo == "DE LAS MODALIDADES DE TRABAJO DE GRADO"
    assert [article.ordinal for article in acuerdos] == ["PRIMERO", "DOS", "TRES"]
    assert all("Calle de los Estudiantes" not in article.texto for article in parsed.articulos)
    assert all("PBX" not in article.texto for article in parsed.articulos)
    assert all("CONSEJO DIRECTIVO-ACUERDO" not in article.texto for article in parsed.articulos)
    art8 = next(article for article in reglamento if article.numero == 8)
    assert any(par.numero is None for par in art8.paragrafos)
    assert [inc.marker for inc in art8.incisos] == list("abcdef")
    art15 = next(article for article in reglamento if article.numero == 15)
    assert [par.numero for par in art15.paragrafos] == ["1", "2", "3"]
    assert [inc.marker for inc in art15.paragrafos[1].incisos] == ["a", "b"]
    assert "Artículo 14" in art15.paragrafos[1].texto
    art19 = next(article for article in reglamento if article.numero == 19)
    assert [inc.marker for inc in art19.incisos] == list("abcdefgh")
    art26 = next(article for article in reglamento if article.numero == 26)
    assert [inc.marker for inc in art26.incisos] == list("abcdefghijklm")
    art27 = next(article for article in reglamento if article.numero == 27)
    assert [par.numero for par in art27.paragrafos] == ["1", "2", "3"]
    assert [inc.marker for inc in art27.paragrafos[1].incisos] == list("abcd")
    assert [inc.marker for inc in art27.paragrafos[2].incisos] == list("abcdefg")
    art30 = next(article for article in reglamento if article.numero == 30)
    assert [par.numero for par in art30.paragrafos] == ["1", "2", "3", "4"]
    assert "una vez se hayan cumplido los objetivos" in art30.paragrafos[0].texto or "una vez se hayan cumplido los objetivos" in art30.texto
