"""Detector de referencias normativas explícitas y extractor estructurado.

Permite reconocer menciones a artículos, parágrafos, incisos y capítulos
para realizar búsquedas exactas en la base SQLite de la versión activa,
garantizando precisión absoluta sin depender exclusivamente de embeddings.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from normativa.corpus import db
from normativa.retrieval.models import RetrievedChunk


@dataclass(frozen=True)
class ExplicitMatch:
    articulo_numero: int | None = None
    articulo_tipo: str = "reglamento"  # "reglamento" o "acuerdo"
    paragrafo_numero: str | None = None
    inciso_marker: str | None = None
    capitulo_numero: int | None = None
    capitulo_romano: str | None = None


# Regex con límites de palabra para evitar falsos positivos (e.g. 15 vs 150)
_ART_RE = re.compile(r"\b(?:art[ií]culo|art\.?)\s*(\d+)\b", re.IGNORECASE)
_PAR_RE = re.compile(r"\bpar[aá]grafo\s*(?:n[uú]mero\s*|n[uú]m\.?\s*)?(\d+|[uú]nico)\b", re.IGNORECASE)
_INC_RE = re.compile(r"\binciso\s*([a-zA-Z])\b", re.IGNORECASE)
_CAP_RE = re.compile(r"\bcap[ií]tulo\s*([ivxlcdm]+|\d+)\b", re.IGNORECASE)

_ROMAN_MAP = {
    "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7,
    "viii": 8, "ix": 9, "x": 10, "xi": 11, "xii": 12, "xiii": 13,
    "xiv": 14, "xv": 15, "xvi": 16, "xvii": 17, "xviii": 18, "xix": 19, "xx": 20,
}


def match_explicit_reference(query: str) -> ExplicitMatch | None:
    """Detecta si la consulta formula una búsqueda explícita de un artículo o capítulo."""
    query_clean = query.strip()
    query_lower = query_clean.lower()

    art_match = _ART_RE.search(query_clean)
    par_match = _PAR_RE.search(query_clean)
    inc_match = _INC_RE.search(query_clean)
    cap_match = _CAP_RE.search(query_clean)

    if not (art_match or cap_match):
        return None

    # Distinguir acuerdo vs reglamento
    # Solo si menciona explícitamente "acuerdo" y no la frase común "de acuerdo con"
    is_acuerdo = False
    if "acuerdo" in query_lower and "de acuerdo con" not in query_lower:
        # Si dice "del acuerdo", "en el acuerdo", "acuerdo aprobatorio", etc.
        if re.search(r"\b(?:del|en\s+el|seg[uú]n\s+el)?\s*acuerdo\b", query_lower):
            is_acuerdo = True

    articulo_numero = int(art_match.group(1)) if art_match else None
    paragrafo_numero = par_match.group(1).lower() if par_match else None
    inciso_marker = inc_match.group(1).lower() if inc_match else None

    capitulo_numero = None
    capitulo_romano = None
    if cap_match:
        raw_cap = cap_match.group(1).lower()
        if raw_cap in _ROMAN_MAP:
            capitulo_numero = _ROMAN_MAP[raw_cap]
            capitulo_romano = raw_cap.upper()
        elif raw_cap.isdigit():
            capitulo_numero = int(raw_cap)

    return ExplicitMatch(
        articulo_numero=articulo_numero,
        articulo_tipo="acuerdo" if is_acuerdo else "reglamento",
        paragrafo_numero=paragrafo_numero,
        inciso_marker=inciso_marker,
        capitulo_numero=capitulo_numero,
        capitulo_romano=capitulo_romano,
    )


def fetch_explicit_chunks(
    db_path: Path | str | None,
    version_id: str,
    match: ExplicitMatch,
) -> list[RetrievedChunk]:
    """Recupera los chunks correspondientes a la referencia explícita desde SQLite."""
    results: list[RetrievedChunk] = []

    with db.get_connection(db_path) as conn:
        if match.articulo_numero is not None:
            # Recuperar todos los chunks de ese artículo (cuerpo, incisos, parágrafos)
            # Ordenados lógicamente: cuerpo primero, luego incisos, luego parágrafos
            cursor = conn.execute(
                """
                SELECT id, version_id, document_id, document_name,
                       capitulo_numero, capitulo_romano, capitulo_titulo,
                       articulo_numero, articulo_ordinal, articulo_tipo,
                       paragrafo_numero, inciso_marker, page_start, page_end,
                       texto, ocr_confidence, location_hint
                FROM chunks
                WHERE version_id = ?
                  AND articulo_numero = ?
                  AND articulo_tipo = ?
                ORDER BY
                  CASE
                    WHEN paragrafo_numero IS NULL AND inciso_marker IS NULL THEN 0
                    WHEN inciso_marker IS NOT NULL THEN 1
                    ELSE 2
                  END,
                  id
                """,
                (version_id, match.articulo_numero, match.articulo_tipo),
            )
            rows = cursor.fetchall()
            for r in rows:
                payload = dict(r)
                payload["origin"] = "explicit_article"
                payload["text"] = r["texto"]
                results.append(
                    RetrievedChunk(
                        chunk_id=r["id"],
                        version_id=version_id,
                        score=1.0,  # Coincidencia exacta
                        payload=payload,
                        text=r["texto"],
                        location_hint=r["location_hint"],
                    )
                )

        elif match.capitulo_numero is not None or match.capitulo_romano is not None:
            # Búsqueda por capítulo
            params: list = [version_id]
            where_clauses = ["version_id = ?"]
            if match.capitulo_numero is not None:
                where_clauses.append("capitulo_numero = ?")
                params.append(match.capitulo_numero)
            elif match.capitulo_romano is not None:
                where_clauses.append("capitulo_romano = ?")
                params.append(match.capitulo_romano)

            cursor = conn.execute(
                f"""
                SELECT id, version_id, document_id, document_name,
                       capitulo_numero, capitulo_romano, capitulo_titulo,
                       articulo_numero, articulo_ordinal, articulo_tipo,
                       paragrafo_numero, inciso_marker, page_start, page_end,
                       texto, ocr_confidence, location_hint
                FROM chunks
                WHERE {' AND '.join(where_clauses)}
                ORDER BY articulo_numero, id
                LIMIT 10
                """,
                params,
            )
            rows = cursor.fetchall()
            for r in rows:
                payload = dict(r)
                payload["origin"] = "explicit_chapter"
                payload["text"] = r["texto"]
                results.append(
                    RetrievedChunk(
                        chunk_id=r["id"],
                        version_id=version_id,
                        score=0.95,
                        payload=payload,
                        text=r["texto"],
                        location_hint=r["location_hint"],
                    )
                )

    if match.paragrafo_numero is not None or match.inciso_marker is not None:
        def subdivision_matches(chunk: RetrievedChunk) -> bool:
            paragraph = (chunk.payload.get("paragrafo_numero") or "").casefold().replace("ú", "u")
            inciso = (chunk.payload.get("inciso_marker") or "").casefold()
            return (
                (match.paragrafo_numero is None or paragraph == match.paragrafo_numero.replace("ú", "u"))
                and (match.inciso_marker is None or inciso == match.inciso_marker)
            )

        results.sort(key=subdivision_matches, reverse=True)
    return results
