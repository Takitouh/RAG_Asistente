from __future__ import annotations

from dataclasses import dataclass, field, asdict
from difflib import SequenceMatcher
from pathlib import Path
import re
import unicodedata

from normativa.ingestion.cleaner import CleanPage, CleanLine
from normativa.ingestion.models import Articulo, Inciso, Paragrafo, ParseRepair, ParseReport, ParsedDocument


ORDINALS = {
    "PRIMERO",
    "SEGUNDO",
    "TERCERO",
    "CUARTO",
    "QUINTO",
    "SEXTO",
    "SEPTIMO",
    "OCTAVO",
    "NOVENO",
    "DECIMO",
    "ONCE",
    "DOCE",
    "TRECE",
    "CATORCE",
    "QUINCE",
    "DIECISEIS",
    "DIECISIETE",
    "DIECIOCHO",
    "DIECINUEVE",
    "VEINTE",
    "UNO",
    "DOS",
    "TRES",
}

ARTICLE_MARKER_RE = re.compile(r"^\s*(ART[ÍI]CULO|ARTICULO)\b", re.IGNORECASE)
CHAPTER_MARKER_RE = re.compile(r"^\s*(CAP[ÍI]TULO|CAPITULO)\b", re.IGNORECASE)
PARAGRAPH_MARKER_RE = re.compile(r"^\s*(PAR[ÁA]GRAFO|PARAGRAFO)\b", re.IGNORECASE)
PUBLISH_RE = re.compile(r"^\s*PUBLI[QC].*", re.IGNORECASE)
NUMBER_TOKEN_RE = re.compile(r"^[\dOolI|!SBZ]+[\.\,:;\-]*$")
ROMAN_TOKEN_RE = re.compile(r"^[IVXLCDM|l!]+$", re.IGNORECASE)
INCISO_TOKEN_RE = re.compile(r"^\s*([A-Za-z0-9|!]{1,3})\s*([.)]{1,2})\s*(.*)$")


@dataclass
class _IncisoBuilder:
    marker: str
    lines: list[str] = field(default_factory=list)
    page_start: int = 0
    page_end: int = 0
    page_confidences: set[float] = field(default_factory=set)


@dataclass
class _ParagrafoBuilder:
    numero: str | None
    lines: list[str] = field(default_factory=list)
    incisos: list[_IncisoBuilder] = field(default_factory=list)
    current_inciso: _IncisoBuilder | None = None
    page_start: int = 0
    page_end: int = 0
    page_confidences: set[float] = field(default_factory=set)


@dataclass
class _ArticleBuilder:
    kind: str
    numero: int | None
    ordinal: str | None
    capitulo_numero: int | None
    capitulo_romano: str | None
    capitulo_titulo: str | None
    body_lines: list[str] = field(default_factory=list)
    incisos: list[_IncisoBuilder] = field(default_factory=list)
    paragrafos: list[_ParagrafoBuilder] = field(default_factory=list)
    current_paragrafo: _ParagrafoBuilder | None = None
    current_inciso: _IncisoBuilder | None = None
    page_start: int = 0
    page_end: int = 0
    page_confidences: set[float] = field(default_factory=set)
    flags: list[str] = field(default_factory=list)
    number_repaired: bool = False


@dataclass(frozen=True, slots=True)
class _LineRecord:
    page_number: int
    text: str
    ocr_confidence: float | None


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _normalize(text: str) -> str:
    text = _strip_accents(text)
    text = text.replace("¡", " ").replace("¿", " ")
    text = re.sub(r"\s+", " ", text.strip())
    return text


def _normalized_upper_ratio(text: str) -> float:
    letters = [char for char in text if char.isalpha()]
    if not letters:
        return 0.0
    upper = sum(1 for char in letters if char.isupper())
    return upper / len(letters)


def _starts_with_marker(text: str, marker: str, threshold: float = 0.85) -> bool:
    normalized = _strip_accents(text).upper()
    first = normalized.split(maxsplit=1)[0] if normalized.split() else ""
    return SequenceMatcher(None, first, marker).ratio() >= threshold


def _first_token(text: str) -> str:
    parts = text.strip().split()
    return parts[0] if parts else ""


def _line_is_upperish(text: str) -> bool:
    return _normalized_upper_ratio(text) >= 0.7


def _is_article_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    first = _first_token(stripped)
    return _starts_with_marker(first, "ARTICULO") and _normalized_upper_ratio(first) >= 0.7


def _is_chapter_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    first = _first_token(stripped)
    return _starts_with_marker(first, "CAPITULO") and _normalized_upper_ratio(first) >= 0.7


def _is_paragraph_heading(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    return _starts_with_marker(stripped, "PARAGRAFO")


def _is_publish_line(text: str) -> bool:
    normalized = _strip_accents(text).upper()
    return normalized.startswith("PUBLI")


def _normalize_number_token(token: str) -> str:
    token = _strip_accents(token).upper()
    translation = str.maketrans({"O": "0", "I": "1", "L": "1", "|": "1", "!": "1", "S": "5", "B": "8", "Z": "2"})
    return token.translate(translation)


def _parse_number_token(token: str) -> int | None:
    cleaned = _normalize_number_token(token)
    cleaned = re.sub(r"[^0-9]", "", cleaned)
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _roman_to_int(token: str) -> int | None:
    cleaned = _strip_accents(token).upper()
    cleaned = cleaned.translate(str.maketrans({"|": "I", "1": "I", "L": "I", "!": "I"}))
    cleaned = re.sub(r"[^IVXLCDM]", "", cleaned)
    if not cleaned:
        return None
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for char in reversed(cleaned):
        value = values[char]
        if value < prev:
            total -= value
        else:
            total += value
            prev = value
    return total


def _parse_ordinal_token(token: str) -> str | None:
    normalized = _strip_accents(token).upper()
    normalized = re.sub(r"[^A-ZÁÉÍÓÚÜÑ]", "", normalized)
    return normalized if normalized in ORDINALS else None


def _clean_token(token: str, is_last: bool) -> str | None:
    if token in {"|", "¡"}:
        return None
    had_symbols = any(symbol in token for symbol in ["|", "[", "]", "¡", "<", ">", ":"])
    cleaned = token.replace("|", "").replace("[", "").replace("]", "").replace("¡", "").replace("<", "").replace(">", "").replace(":", "")
    cleaned = cleaned.strip()
    if not cleaned:
        return None
    if is_last and had_symbols and len(cleaned) <= 3:
        return None
    return cleaned


def _reflow_lines(lines: list[str]) -> str:
    if not lines:
        return ""
    result = ""
    for raw_line in lines:
        text = raw_line.strip()
        if not text:
            continue
        if result.endswith("-") and text[:1].islower():
            result = result[:-1] + text
        else:
            result = f"{result} {text}".strip()
    return re.sub(r"\s+", " ", result).strip()


def _clean_content_text(text: str) -> str:
    tokens = text.split()
    cleaned_tokens: list[str] = []
    for index, token in enumerate(tokens):
        cleaned = _clean_token(token, index == len(tokens) - 1)
        if cleaned:
            cleaned_tokens.append(cleaned)
    return " ".join(cleaned_tokens).strip()


def _finalize_inciso(builder: _IncisoBuilder | None) -> Inciso | None:
    if builder is None:
        return None
    return Inciso(marker=builder.marker, texto=_clean_content_text(_reflow_lines(builder.lines)))


def _finalize_paragrafo(builder: _ParagrafoBuilder | None) -> Paragrafo | None:
    if builder is None:
        return None
    incisos = [_finalize_inciso(inciso) for inciso in builder.incisos]
    return Paragrafo(
        numero=builder.numero,
        texto=_clean_content_text(_reflow_lines(builder.lines)),
        incisos=[inciso for inciso in incisos if inciso is not None],
    )


def _finalize_article(builder: _ArticleBuilder, page_confidences: dict[int, float | None]) -> Articulo:
    paragrafos = [_finalize_paragrafo(par) for par in builder.paragrafos]
    incisos = [_finalize_inciso(inc) for inc in builder.incisos]
    paragrafos = [par for par in paragrafos if par is not None]
    incisos = [inc for inc in incisos if inc is not None]

    body_text = _clean_content_text(_reflow_lines(builder.body_lines))
    page_numbers = list(range(builder.page_start, builder.page_end + 1)) if builder.page_start and builder.page_end else []
    confidences = [page_confidences.get(page) for page in page_numbers if page_confidences.get(page) is not None]
    confidence_mean = sum(confidences) / len(confidences) if confidences else None

    flags: list[str] = list(builder.flags)
    if builder.number_repaired and "numero_reparado" not in flags:
        flags.append("numero_reparado")
    if confidence_mean is not None and confidence_mean < 85 and "baja_confianza_ocr" not in flags:
        flags.append("baja_confianza_ocr")
    has_content = bool(body_text.strip() or any(par.text.strip() for par in paragrafos) or any(inc.text.strip() for inc in incisos))
    if not has_content and "sin_texto" not in flags:
        flags.append("sin_texto")

    return Articulo(
        kind=builder.kind,  # type: ignore[arg-type]
        numero=builder.numero,
        ordinal=builder.ordinal,
        capitulo_numero=builder.capitulo_numero,
        capitulo_romano=builder.capitulo_romano,
        capitulo_titulo=builder.capitulo_titulo,
        texto=body_text,
        incisos=incisos,
        paragrafos=paragrafos,
        page_start=builder.page_start,
        page_end=builder.page_end,
        ocr_confidence_mean=confidence_mean,
        flags=flags,
    )


def _capture_lines(clean_pages: list[CleanPage]) -> tuple[list[_LineRecord], dict[int, float | None]]:
    records: list[_LineRecord] = []
    page_confidences = {page.page_number: page.ocr_confidence for page in clean_pages}
    for page in clean_pages:
        for line in page.lines:
            records.append(_LineRecord(page.page_number, line.text, page.ocr_confidence))
    return records, page_confidences


def _parse_chapter_header(line: str, expected: int) -> tuple[int | None, str | None, str | None]:
    if not _is_chapter_heading(line):
        return None, None, None
    parts = line.strip().split()
    if len(parts) < 2:
        return expected, "I" if expected == 1 else None, ""
    raw_numeral = parts[1]
    numeral = _roman_to_int(raw_numeral)
    roman_clean = _strip_accents(raw_numeral).upper().translate(str.maketrans({"|": "I", "1": "I", "L": "I", "!": "I"}))
    title = " ".join(parts[2:]).strip()
    if numeral is None:
        numeral = expected
    return numeral, roman_clean or None, title


def _parse_article_header(line: str) -> dict[str, object] | None:
    if not _is_article_heading(line):
        return None
    parts = line.strip().split()
    if len(parts) < 2:
        return None
    token = parts[1]
    ordinal = _parse_ordinal_token(token)
    kind = "acuerdo" if ordinal else "reglamento"
    number = None if ordinal else _parse_number_token(token)
    remainder = " ".join(parts[2:]).strip()
    return {
        "kind": kind,
        "number": number,
        "ordinal": ordinal,
        "remainder": remainder,
        "original": line,
        "token": token,
    }


def _parse_paragraph_header(line: str) -> tuple[str | None, str]:
    if not _is_paragraph_heading(line):
        return None, ""
    parts = line.strip().split()
    if len(parts) < 2:
        return None, ""
    token = parts[1]
    token_clean = re.sub(r"[.\-:,;]", "", token)
    numericish = bool(re.search(r"\d", token_clean) or re.fullmatch(r"[|!lI0OSBZ]+", token_clean))
    if numericish:
        number = re.sub(r"[^0-9]", "", _normalize_number_token(token))
        return (number or None), " ".join(parts[2:]).strip()
    return None, " ".join(parts[1:]).strip()


def _parse_inciso_header(line: str, expected: str | int | None, expected_kind: str | None) -> tuple[str | None, str, str] | None:
    match = INCISO_TOKEN_RE.match(line)
    if not match:
        return None
    raw_marker, sep, remainder = match.groups()
    marker = _strip_accents(raw_marker).lower()
    if marker in {"c", "cc"}:
        marker = "c"
    elif marker in {"9"}:
        marker = "g"
    elif marker in {"0"}:
        marker = "o"
    elif marker in {"1", "|", "l", "i", "!"}:
        marker = "l" if expected_kind == "letter" and expected == "l" else "i" if expected_kind == "letter" and expected == "i" else "1"
    if expected_kind == "letter" and isinstance(expected, str):
        if marker != expected:
            if marker in {"l", "i"} and expected in {"l", "i"}:
                marker = expected
            else:
                return None
    elif expected_kind == "digit" and isinstance(expected, int):
        if marker != str(expected):
            if marker == "1" and expected == 1:
                marker = "1"
            else:
                return None
    return marker, sep, remainder


def _next_article_candidate(records: list[_LineRecord], start: int) -> tuple[int | None, int | None]:
    for index in range(start, len(records)):
        parsed = _parse_article_header(records[index].text)
        if parsed is None:
            continue
        if parsed["kind"] == "reglamento" and parsed["number"] is not None:
            return int(parsed["number"]), index
    return None, None


def _next_chapter_candidate(records: list[_LineRecord], start: int) -> tuple[int | None, int | None]:
    for index in range(start, len(records)):
        if not _is_chapter_heading(records[index].text):
            continue
        numeral, _, _ = _parse_chapter_header(records[index].text, 1)
        if numeral is not None:
            return numeral, index
    return None, None


def parse_document(clean_pages: list[CleanPage], source_file: str) -> ParsedDocument:
    records, page_confidences = _capture_lines(clean_pages)
    preamble_lines: list[str] = []
    cierre_lines: list[str] = []
    articles: list[Articulo] = []
    repairs: list[ParseRepair] = []
    anomalies: list[str] = []
    current_chapter_num: int | None = None
    current_chapter_roman: str | None = None
    current_chapter_title: str | None = None
    current_article: _ArticleBuilder | None = None
    numeric_expected = 1
    chapter_expected = 1
    i = 0

    def flush_open_blocks(article: _ArticleBuilder) -> None:
        if article.current_inciso is not None:
            if article.current_paragrafo is not None:
                article.current_paragrafo.incisos.append(article.current_inciso)
            else:
                article.incisos.append(article.current_inciso)
            article.current_inciso = None
        if article.current_paragrafo is not None:
            article.paragrafos.append(article.current_paragrafo)
            article.current_paragrafo = None

    def finish_current_article() -> None:
        nonlocal current_article
        if current_article is None:
            return
        flush_open_blocks(current_article)
        article = _finalize_article(current_article, page_confidences)
        articles.append(article)
        current_article = None

    def ensure_article_builder(kind: str, number: int | None, ordinal: str | None, page_number: int) -> None:
        nonlocal current_article
        current_article = _ArticleBuilder(
            kind=kind,
            numero=number,
            ordinal=ordinal,
            capitulo_numero=current_chapter_num,
            capitulo_romano=current_chapter_roman,
            capitulo_titulo=current_chapter_title,
            page_start=page_number,
            page_end=page_number,
        )

    while i < len(records):
        record = records[i]
        text = record.text.strip()
        if not text:
            i += 1
            continue

        if _is_publish_line(text):
            finish_current_article()
            cierre_lines.append(text)
            i += 1
            while i < len(records):
                cierre_lines.append(records[i].text.strip())
                i += 1
            break

        if _is_chapter_heading(text):
            finish_current_article()
            chapter_num, chapter_roman, _ = _parse_chapter_header(text, chapter_expected)
            if chapter_num is None:
                anomalies.append(f"Capítulo no reconocido en página {record.page_number}: {text}")
                i += 1
                continue
            expected = chapter_expected
            if chapter_num != expected:
                next_candidate, _ = _next_chapter_candidate(records, i + 1)
                if next_candidate == expected + 1:
                    repairs.append(ParseRepair(record.page_number, text, f"CAPÍTULO {expected}", "capítulo reparado por secuencia"))
                    chapter_num = expected
                else:
                    anomalies.append(f"Capítulo fuera de secuencia en página {record.page_number}: {text}")
            current_chapter_num = chapter_num
            current_chapter_roman = chapter_roman or str(chapter_num)
            title_lines: list[str] = []
            j = i + 1
            while j < len(records):
                candidate = records[j].text.strip()
                if not candidate:
                    j += 1
                    continue
                if _is_article_heading(candidate) or _is_chapter_heading(candidate) or _is_paragraph_heading(candidate) or _is_publish_line(candidate):
                    break
                if _line_is_upperish(candidate) and len(title_lines) < 2:
                    title_lines.append(candidate)
                    j += 1
                    continue
                break
            current_chapter_title = _clean_content_text(_reflow_lines(title_lines)) or None
            chapter_expected = chapter_num + 1
            i = j
            continue

        article_header = _parse_article_header(text)
        if article_header is not None:
            if current_article is not None:
                finish_current_article()
            kind = str(article_header["kind"])
            token = str(article_header["token"])
            ordinal = article_header["ordinal"]  # type: ignore[assignment]
            number = article_header["number"]  # type: ignore[assignment]
            remainder = str(article_header["remainder"])
            if kind == "reglamento":
                if number is None:
                    anomalies.append(f"Artículo sin número en página {record.page_number}: {text}")
                    i += 1
                    continue
                if number != numeric_expected:
                    next_candidate, _ = _next_article_candidate(records, i + 1)
                    if next_candidate == numeric_expected + 1:
                        repairs.append(ParseRepair(record.page_number, text, f"ARTÍCULO {numeric_expected}", "artículo reparado por secuencia"))
                        number = numeric_expected
                        number_repaired = True
                    else:
                        anomalies.append(f"Artículo fuera de secuencia en página {record.page_number}: {text}")
                        i += 1
                        continue
                else:
                    number_repaired = False
                numeric_expected = int(number) + 1
            else:
                number_repaired = False
            ensure_article_builder(kind, int(number) if number is not None else None, ordinal if isinstance(ordinal, str) else None, record.page_number)
            current_article.number_repaired = number_repaired
            current_article.page_end = record.page_number
            if record.ocr_confidence is not None:
                current_article.page_confidences.add(record.ocr_confidence)
            if remainder:
                current_article.body_lines.append(remainder)
            i += 1
            continue

        if current_article is None:
            preamble_lines.append(text)
            i += 1
            continue

        if _is_paragraph_heading(text):
            paragraph_header = _parse_paragraph_header(text)
            flush_open_blocks(current_article)
            current_article.current_paragrafo = _ParagrafoBuilder(numero=paragraph_header[0], page_start=record.page_number, page_end=record.page_number)
            current_article.page_end = record.page_number
            if record.ocr_confidence is not None:
                current_article.page_confidences.add(record.ocr_confidence)
            if paragraph_header[1]:
                current_article.current_paragrafo.lines.append(paragraph_header[1])
            i += 1
            continue

        current_context_paragraph = current_article.current_paragrafo
        expected_kind = getattr(current_context_paragraph, "_expected_kind", None) if current_context_paragraph is not None else getattr(current_article, "_expected_kind", None)
        expected_value = getattr(current_context_paragraph, "_expected_value", None) if current_context_paragraph is not None else getattr(current_article, "_expected_value", None)
        parsed_inciso = _parse_inciso_header(text, expected_value, expected_kind)
        if parsed_inciso is not None:
            marker, sep, remainder = parsed_inciso
            if current_context_paragraph is not None:
                if current_context_paragraph.current_inciso is not None:
                    current_context_paragraph.incisos.append(current_context_paragraph.current_inciso)
                    current_context_paragraph.current_inciso = None
                new_inciso = _IncisoBuilder(marker=marker, page_start=record.page_number, page_end=record.page_number)
                if record.ocr_confidence is not None:
                    current_context_paragraph.page_confidences.add(record.ocr_confidence)
                if remainder:
                    new_inciso.lines.append(remainder)
                current_context_paragraph.current_inciso = new_inciso
                if marker.isdigit():
                    current_context_paragraph._expected_kind = "digit"  # type: ignore[attr-defined]
                    current_context_paragraph._expected_value = int(marker) + 1  # type: ignore[attr-defined]
                else:
                    current_context_paragraph._expected_kind = "letter"  # type: ignore[attr-defined]
                    current_context_paragraph._expected_value = chr(ord(marker) + 1)  # type: ignore[attr-defined]
                i += 1
                continue
            if current_article.current_inciso is not None:
                current_article.incisos.append(current_article.current_inciso)
                current_article.current_inciso = None
            new_inciso = _IncisoBuilder(marker=marker, page_start=record.page_number, page_end=record.page_number)
            if record.ocr_confidence is not None:
                current_article.page_confidences.add(record.ocr_confidence)
            if remainder:
                new_inciso.lines.append(remainder)
            current_article.current_inciso = new_inciso
            if marker.isdigit():
                current_article._expected_kind = "digit"  # type: ignore[attr-defined]
                current_article._expected_value = int(marker) + 1  # type: ignore[attr-defined]
            else:
                current_article._expected_kind = "letter"  # type: ignore[attr-defined]
                current_article._expected_value = chr(ord(marker) + 1)  # type: ignore[attr-defined]
            i += 1
            continue

        # continuation lines
        if current_article.current_paragrafo is not None and current_article.current_paragrafo.current_inciso is not None:
            current_article.current_paragrafo.current_inciso.lines.append(text)
            current_article.current_paragrafo.current_inciso.page_end = record.page_number
            if record.ocr_confidence is not None:
                current_article.current_paragrafo.current_inciso.page_confidences.add(record.ocr_confidence)
        elif current_article.current_inciso is not None:
            current_article.current_inciso.lines.append(text)
            current_article.current_inciso.page_end = record.page_number
            if record.ocr_confidence is not None:
                current_article.current_inciso.page_confidences.add(record.ocr_confidence)
        elif current_article.current_paragrafo is not None:
            current_article.current_paragrafo.lines.append(text)
            current_article.current_paragrafo.page_end = record.page_number
            if record.ocr_confidence is not None:
                current_article.current_paragrafo.page_confidences.add(record.ocr_confidence)
        else:
            current_article.body_lines.append(text)
        current_article.page_end = record.page_number
        if record.ocr_confidence is not None:
            current_article.page_confidences.add(record.ocr_confidence)
        i += 1

    finish_current_article()

    # Finalize paragraph/inciso builders that may still be attached to articles after loop
    final_articles: list[Articulo] = []
    for article in articles:
        final_articles.append(article)

    preambulo = _clean_content_text(_reflow_lines(preamble_lines))
    cierre = _clean_content_text(_reflow_lines(cierre_lines))

    # statistics
    statistics_map = {
        "capitulos": len({article.capitulo_numero for article in final_articles if article.capitulo_numero is not None}),
        "articulos_reglamento": sum(1 for article in final_articles if article.kind == "reglamento"),
        "articulos_acuerdo": sum(1 for article in final_articles if article.kind == "acuerdo"),
        "paragrafos": sum(len(article.paragrafos) for article in final_articles),
        "incisos": sum(len(article.incisos) + sum(len(par.incisos) for par in article.paragrafos) for article in final_articles),
    }
    for article in final_articles:
        if article.flags:
            for flag in article.flags:
                statistics_map[f"flag_{flag}"] = statistics_map.get(f"flag_{flag}", 0) + 1

    numeric_articles = [article.numero for article in final_articles if article.kind == "reglamento" and article.numero is not None]
    if numeric_articles:
        maximum = max(numeric_articles)
        expected_numbers = list(range(1, maximum + 1))
        missing = sorted(set(expected_numbers) - set(numeric_articles))
        duplicated = sorted(number for number in expected_numbers if numeric_articles.count(number) > 1)
        if missing:
            anomalies.append(f"Faltan artículos reglamento: {missing}")
        if duplicated:
            anomalies.append(f"Artículos reglamento duplicados: {duplicated}")

    chapter_numbers = [article.capitulo_numero for article in final_articles if article.capitulo_numero is not None]
    if chapter_numbers:
        expected = list(range(1, max(chapter_numbers) + 1))
        unique_chapters = []
        for value in chapter_numbers:
            if value not in unique_chapters:
                unique_chapters.append(value)
        if unique_chapters != expected:
            anomalies.append(f"Capítulos fuera de secuencia: {unique_chapters}")

    for article in final_articles:
        if not (article.texto.strip() or any(par.texto.strip() for par in article.paragrafos) or any(inc.texto.strip() for inc in article.incisos)):
            anomalies.append(f"Artículo sin cuerpo en página {article.page_start}: {article.kind} {article.numero or article.ordinal}")

    # Add cleaner anomalies and structural line protection anomalies.
    for page in clean_pages:
        anomalies.extend(page.anomalies)

    report = ParseReport(
        repairs=repairs,
        anomalies=anomalies,
        removed_lines_count=sum(page.removed_count for page in clean_pages),
        statistics=statistics_map,
    )
    return ParsedDocument(
        source_file=source_file,
        num_pages=len(clean_pages),
        preambulo=preambulo,
        articulos=final_articles,
        cierre=cierre,
        report=report,
    )


def render_parsed_preview(parsed: ParsedDocument) -> str:
    lines: list[str] = [f"# {parsed.source_file}", ""]
    grouped: dict[tuple[int | None, str | None, str | None], list[Articulo]] = {}
    for article in parsed.articulos:
        key = (article.capitulo_numero, article.capitulo_romano, article.capitulo_titulo)
        grouped.setdefault(key, []).append(article)

    if parsed.preambulo:
        lines.extend(["## Preámbulo", parsed.preambulo, ""])

    if parsed.articulos and parsed.articulos[0].kind == "acuerdo":
        agreement_articles = [article for article in parsed.articulos if article.kind == "acuerdo"]
        if agreement_articles:
            lines.append("## Acuerdo")
            for article in agreement_articles:
                header = f"Artículo {article.ordinal or article.numero}"
                lines.extend([f"### {header}", article.texto])
                for par in article.paragrafos:
                    lines.append(f"- Parágrafo {par.numero or 'único'}: {par.texto}")
                    for inc in par.incisos:
                        lines.append(f"  - {inc.marker}: {inc.texto}")
                for inc in article.incisos:
                    lines.append(f"- {inc.marker}: {inc.texto}")
                lines.append("")

    for key in sorted((k for k in grouped if k[0] is not None), key=lambda item: item[0] or 0):
        chapter_articles = grouped[key]
        chapter_title = chapter_articles[0].capitulo_titulo or ""
        roman = chapter_articles[0].capitulo_romano or ""
        lines.append(f"## Capítulo {roman}{' - ' + chapter_title if chapter_title else ''}")
        for article in chapter_articles:
            head = f"Artículo {article.numero}" if article.numero is not None else f"Artículo {article.ordinal}"
            lines.append(f"### {head}")
            if article.texto:
                lines.append(article.texto)
            for par in article.paragrafos:
                lines.append(f"- Parágrafo {par.numero or 'único'}: {par.texto}")
                for inc in par.incisos:
                    lines.append(f"  - {inc.marker}: {inc.texto}")
            for inc in article.incisos:
                lines.append(f"- {inc.marker}: {inc.texto}")
            lines.append("")

    if parsed.cierre:
        lines.extend(["## Cierre", parsed.cierre, ""])

    return "\n".join(lines).rstrip() + "\n"


def render_parse_report(parsed: ParsedDocument) -> str:
    lines: list[str] = []
    lines.append("Reparaciones:")
    if parsed.report.repairs:
        for repair in parsed.report.repairs:
            lines.append(f"  Página {repair.pagina}: {repair.original} -> {repair.corregido} [{repair.motivo}]")
    else:
        lines.append("  Ninguna")
    lines.append("")
    lines.append("Anomalías:")
    if parsed.report.anomalies:
        lines.extend(f"  - {item}" for item in parsed.report.anomalies)
    else:
        lines.append("  Ninguna")
    lines.append("")
    lines.append("Estadísticas:")
    for key, value in sorted(parsed.report.statistics.items()):
        lines.append(f"  {key}: {value}")
    lines.append("")
    lines.append("Artículos con flags:")
    flagged = [article for article in parsed.articulos if article.flags]
    if flagged:
        for article in flagged:
            ident = article.numero if article.numero is not None else article.ordinal
            lines.append(f"  - {article.kind} {ident}: {', '.join(article.flags)}")
    else:
        lines.append("  Ninguno")
    return "\n".join(lines).rstrip() + "\n"
