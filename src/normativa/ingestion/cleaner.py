from __future__ import annotations

import re
import statistics
import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from difflib import SequenceMatcher

from normativa.ingestion.extractor import LineInfo, PageText


@dataclass(frozen=True, slots=True)
class CleanLine:
    text: str
    y_top_norm: float
    y_bottom_norm: float


@dataclass(frozen=True, slots=True)
class CleanPage:
    page_number: int
    ocr_confidence: float | None
    lines: list[CleanLine]
    removed_count: int = 0
    anomalies: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RemovedLine:
    page_number: int
    y_top_norm: float
    reason: str
    original: str


@dataclass(frozen=True, slots=True)
class CleaningLog:
    removed_lines: list[RemovedLine]
    anomalies: list[str]
    statistics: dict[str, int]


HEADER_ZONE_LIMIT = 0.25
FOOTER_ZONE_LIMIT = 0.80
SIMILARITY_THRESHOLD = 0.80
GROUP_REPEAT_THRESHOLD = 0.40
MIN_REPEAT_PAGES = 3

STRUCTURAL_LINE_RE = re.compile(r"^(ART[ÍI]CULO|ARTICULO|CAP[ÍI]TULO|CAPITULO|PAR[ÁA]GRAFO|PARAGRAFO)\b", re.IGNORECASE)
INDEX_CHAPTER_RE = re.compile(r"^CAP[ÍI]TULO\s+[IVXLCDMIlV0-9|]+\s*-\s+.+$", re.IGNORECASE)
INDEX_START_RE = re.compile(r"^í?ndice(?:\s+general)?$", re.IGNORECASE)
LETTER_SEQ_RE = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}")


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _normalize_group_text(text: str) -> str:
    text = _strip_accents(text).lower()
    text = re.sub(r"\d", "#", text)
    text = re.sub(r"[^a-z#\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _is_structural_line(text: str) -> bool:
    return bool(STRUCTURAL_LINE_RE.match(text.strip()))


def _line_is_noise(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if _is_structural_line(stripped):
        return False
    if re.search(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{3,}", stripped):
        return False
    if len(re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]", stripped)) <= 2 and len(stripped) <= 5:
        return True
    return False


def _is_index_entry(text: str) -> bool:
    return bool(INDEX_CHAPTER_RE.match(text.strip()))


def _cluster_repeated_lines(records: list[tuple[int, int, float, float, str]], total_pages: int) -> list[dict[str, object]]:
    clusters: list[dict[str, object]] = []
    for page_number, line_index, y_top, y_bottom, text in records:
        normalized = _normalize_group_text(text)
        if not normalized:
            continue
        matched = None
        for cluster in clusters:
            if SequenceMatcher(None, normalized, cluster["representative"]).ratio() >= SIMILARITY_THRESHOLD:
                matched = cluster
                break
        if matched is None:
            matched = {
                "representative": normalized,
                "pages": set(),
                "items": [],
            }
            clusters.append(matched)
        matched["pages"].add(page_number)
        matched["items"].append((page_number, line_index, y_top, y_bottom, text))

    threshold = None
    if total_pages >= 3:
        threshold = max(MIN_REPEAT_PAGES, int(total_pages * GROUP_REPEAT_THRESHOLD + 0.999))

    repeated = []
    for cluster in clusters:
        if threshold is not None and len(cluster["pages"]) >= threshold:
            repeated.append(cluster)
    return repeated


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def clean_pages(pages: list[PageText]) -> tuple[list[CleanPage], CleaningLog]:
    removed_lines: list[RemovedLine] = []
    anomalies: list[str] = []
    statistics_map: dict[str, int] = {
        "pages": len(pages),
        "removed_header_footer": 0,
        "removed_noise": 0,
        "removed_index": 0,
    }

    all_records: list[tuple[int, int, float, float, str]] = []
    page_lines: dict[int, list[tuple[int, float, float, str]]] = defaultdict(list)
    for page in pages:
        for idx, line in enumerate(page.lines):
            all_records.append((page.page_number, idx, line.y_top_norm, line.y_bottom_norm, line.text))
            page_lines[page.page_number].append((idx, line.y_top_norm, line.y_bottom_norm, line.text))

    top_candidates = [record for record in all_records if record[2] < HEADER_ZONE_LIMIT]
    bottom_candidates = [record for record in all_records if record[2] > FOOTER_ZONE_LIMIT]
    top_clusters = _cluster_repeated_lines(top_candidates, len(pages))
    bottom_clusters = _cluster_repeated_lines(bottom_candidates, len(pages))

    header_end_by_page: dict[int, float] = {}
    footer_start_by_page: dict[int, float] = {}

    for page in pages:
        top_hits = []
        for cluster in top_clusters:
            for page_number, _, _, y_bottom, text in cluster["items"]:
                if page_number == page.page_number:
                    top_hits.append(y_bottom)
        if top_hits:
            header_end_by_page[page.page_number] = max(top_hits)

        bottom_hits = []
        for cluster in bottom_clusters:
            for page_number, _, y_top, _, text in cluster["items"]:
                if page_number == page.page_number:
                    bottom_hits.append(y_top)
        if bottom_hits:
            footer_start_by_page[page.page_number] = min(bottom_hits)

    header_backup = _median(list(header_end_by_page.values()))
    footer_backup = _median(list(footer_start_by_page.values()))

    keep_map: dict[tuple[int, int], bool] = {}
    index_started = False
    index_ended = False
    index_last_page = None
    for page in pages:
        page_anomalies: list[str] = []
        header_end = header_end_by_page.get(page.page_number, header_backup)
        footer_start = footer_start_by_page.get(page.page_number, footer_backup)
        for idx, line in enumerate(page.lines):
            key = (page.page_number, idx)
            text = line.text
            if header_end is not None and line.y_top_norm <= header_end:
                if _is_structural_line(text) and not _is_index_entry(text):
                    message = f"Protegida por encabezado/pie: página {page.page_number}: {text}"
                    anomalies.append(message)
                    page_anomalies.append(message)
                    keep_map[key] = True
                else:
                    keep_map[key] = False
                    removed_lines.append(RemovedLine(page.page_number, line.y_top_norm, "header", text))
                    statistics_map["removed_header_footer"] += 1
                    continue
            elif footer_start is not None and line.y_top_norm >= footer_start - 0.005:
                if _is_structural_line(text) and not _is_index_entry(text):
                    message = f"Protegida por encabezado/pie: página {page.page_number}: {text}"
                    anomalies.append(message)
                    page_anomalies.append(message)
                    keep_map[key] = True
                else:
                    keep_map[key] = False
                    removed_lines.append(RemovedLine(page.page_number, line.y_top_norm, "footer", text))
                    statistics_map["removed_header_footer"] += 1
                    continue
            else:
                keep_map[key] = True

    # noise and index pass
    clean_pages_out: list[CleanPage] = []
    index_hit = False
    for page in pages:
        page_out_lines: list[CleanLine] = []
        page_anomalies: list[str] = []
        page_removed = 0
        page_index_mode = False
        for idx, line in enumerate(page.lines):
            key = (page.page_number, idx)
            if not keep_map.get(key, True):
                page_removed += 1
                continue
            text = line.text
            if INDEX_START_RE.match(_strip_accents(text).strip()):
                index_started = True
                index_hit = True
                page_index_mode = True
                removed_lines.append(RemovedLine(page.page_number, line.y_top_norm, "index", text))
                statistics_map["removed_index"] += 1
                page_removed += 1
                continue
            if _is_index_entry(text):
                index_hit = True
                index_last_page = page.page_number
                removed_lines.append(RemovedLine(page.page_number, line.y_top_norm, "index", text))
                statistics_map["removed_index"] += 1
                page_removed += 1
                continue
            if _line_is_noise(text):
                removed_lines.append(RemovedLine(page.page_number, line.y_top_norm, "ruido", text))
                statistics_map["removed_noise"] += 1
                page_removed += 1
                continue
            page_out_lines.append(CleanLine(text=text, y_top_norm=line.y_top_norm, y_bottom_norm=line.y_bottom_norm))
        clean_pages_out.append(
            CleanPage(
                page_number=page.page_number,
                ocr_confidence=page.ocr_confidence,
                lines=page_out_lines,
                removed_count=page_removed,
                anomalies=page_anomalies,
            )
        )

    return clean_pages_out, CleaningLog(removed_lines=removed_lines, anomalies=anomalies, statistics=statistics_map)


def render_cleaning_log(log: CleaningLog) -> str:
    lines = ["Líneas eliminadas:"]
    for item in log.removed_lines:
        lines.append(f"  Página {item.page_number} y={item.y_top_norm:.3f} [{item.reason}] {item.original}")
    lines.append("")
    lines.append("Anomalías:")
    for item in log.anomalies:
        lines.append(f"  - {item}")
    lines.append("")
    lines.append("Estadísticas:")
    for key, value in sorted(log.statistics.items()):
        lines.append(f"  {key}: {value}")
    return "\n".join(lines).rstrip() + "\n"
