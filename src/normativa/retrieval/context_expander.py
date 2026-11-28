"""Expansión por unidad documental dentro de una misma versión."""
from __future__ import annotations

import re
from pathlib import Path

from normativa.corpus import db
from normativa.retrieval.models import RetrievedChunk

_ACTIVITY = "actividad_procedimiento"
_SUBSECTION = re.compile(r"(?<![\d.])(\d+(?:\.\d+)*)(?:\s+[^/\n]+?/)?\s+Actividad\s+\d+\b", re.IGNORECASE)


def procedure_subsection(location: str) -> str | None:
    match = _SUBSECTION.search(location)
    return match[1] if match else None


def structural_unit(chunk: RetrievedChunk) -> tuple:
    number = chunk.payload.get("articulo_numero")
    kind = chunk.payload.get("articulo_tipo", "reglamento")
    if number is None:
        return (chunk.version_id, chunk.chunk_id)
    section = procedure_subsection(chunk.location_hint) if kind == _ACTIVITY else None
    return (chunk.version_id, kind, int(number), section)


def _document_order(chunk: RetrievedChunk) -> tuple:
    payload = chunk.payload
    paragraph = payload.get("paragrafo_numero") or ""
    literal = payload.get("inciso_marker") or ""
    return (
        payload.get("capitulo_numero") or 0,
        payload.get("articulo_numero") or 0,
        bool(paragraph), str(paragraph), str(literal), chunk.chunk_id,
    )


def expand_normative_context(
    initial_chunks: list[RetrievedChunk],
    db_path: Path | str | None,
    version_id: str,
    query: str = "",
) -> list[RetrievedChunk]:
    """Añade subdivisiones de artículos o actividades vecinas del mismo subnumeral."""
    initial = [chunk for chunk in initial_chunks if chunk.version_id == version_id]
    anchors: dict[tuple, RetrievedChunk] = {}
    for chunk in initial:
        unit = structural_unit(chunk)
        if len(unit) == 4:
            anchors.setdefault(unit, chunk)
    if not anchors:
        return initial

    expanded = {chunk.chunk_id: chunk for chunk in initial}
    with db.get_connection(db_path) as conn:
        for (_, kind, number, subsection), seed in anchors.items():
            if kind == _ACTIVITY and subsection is None:
                continue
            distance = 1 if kind == _ACTIVITY else 0
            rows = conn.execute(
                """
                SELECT * FROM chunks
                WHERE version_id = ? AND articulo_tipo = ?
                  AND articulo_numero BETWEEN ? AND ?
                """,
                (version_id, kind, number - distance, number + distance),
            )
            for row in rows:
                location = row["location_hint"]
                if row["id"] in expanded or (kind == _ACTIVITY and procedure_subsection(location) != subsection):
                    continue
                expanded[row["id"]] = RetrievedChunk(
                    chunk_id=row["id"], version_id=version_id, score=seed.score,
                    payload={**dict(row), "origin": "context_expansion"},
                    text=row["texto"], location_hint=location,
                )
    if len(expanded) == len(initial):
        return initial
    return sorted(expanded.values(), key=_document_order)
