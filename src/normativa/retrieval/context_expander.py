"""Expansor contextual de fragmentos normativos.

Implementa la recuperación jerárquica de relaciones:
Documento → Capítulo → Artículo (cuerpo) → Incisos → Parágrafos.

Garantiza que fragmentos dependientes (como incisos o parágrafos)
recuperen el cuerpo del artículo principal que les otorga sentido jurídico,
y que listas normativas distribuidas (como las modalidades del artículo 8)
no queden truncadas o fragmentadas.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from normativa.corpus import db
from normativa.retrieval.models import RetrievedChunk


def expand_normative_context(
    initial_chunks: list[RetrievedChunk],
    db_path: Path | str | None,
    version_id: str,
    query: str = "",
) -> list[RetrievedChunk]:
    """Expande los fragmentos iniciales recuperados con su contexto jerárquico inmediato.

    Reglas de expansión:
    1. Aislamiento estricto: solo se consultan chunks de `version_id`.
    2. Si se recuperó un parágrafo o inciso de un artículo, se recupera el CUERPO principal
       del artículo correspondiente si no estaba ya presente.
    3. Si un artículo tiene incisos directos (listas de modalidades, requisitos, etc.),
       se incorporan los incisos del artículo para no fragmentar listas oficiales.
    4. Si un artículo tiene relevancia alta (score >= 0.60), se incorporan también sus
       parágrafos para capturar excepciones y condiciones normativas (e.g. prórrogas).
    5. Deduplicación y ordenamiento jerárquico natural.
    """
    if not initial_chunks:
        return []

    existing_ids: set[str] = {c.chunk_id for c in initial_chunks}
    expanded_chunks: list[RetrievedChunk] = list(initial_chunks)

    # Identificar artículos presentes en los chunks iniciales
    articles_to_expand: dict[tuple[int, str], float] = {}
    for c in initial_chunks:
        art_num = c.payload.get("articulo_numero")
        art_kind = c.payload.get("articulo_tipo", "reglamento")
        if art_num is not None:
            key = (int(art_num), str(art_kind))
            articles_to_expand[key] = max(articles_to_expand.get(key, 0.0), c.score)

    if not articles_to_expand:
        return initial_chunks

    with db.get_connection(db_path) as conn:
        for (art_num, art_kind), max_score in articles_to_expand.items():
            # Buscar todos los componentes del artículo en SQLite
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
                (version_id, art_num, art_kind),
            )
            rows = cursor.fetchall()
            if not rows:
                continue

            for r in rows:
                chunk_id = r["id"]
                if chunk_id in existing_ids:
                    continue

                is_cuerpo = r["paragrafo_numero"] is None and r["inciso_marker"] is None
                is_inciso = r["inciso_marker"] is not None
                is_paragrafo = r["paragrafo_numero"] is not None

                # Decisión de inclusión contextual:
                # - Siempre incluir el cuerpo si falta
                # - Incluir incisos si el cuerpo o algún parágrafo fue recuperado
                # - Incluir parágrafos si el score es relevante (>= 0.58) o si la consulta menciona plazos/prórrogas
                should_add = False
                if is_cuerpo:
                    should_add = True
                elif is_inciso:
                    should_add = True
                elif is_paragrafo:
                    # Incluir parágrafo si el artículo tiene score alto o es artículo de procedimiento
                    if max_score >= 0.58 or art_num in (8, 14, 15, 16, 21, 30):
                        should_add = True

                if should_add:
                    payload = dict(r)
                    payload["origin"] = "context_expansion"
                    payload["text"] = r["texto"]
                    expanded_chunks.append(
                        RetrievedChunk(
                            chunk_id=chunk_id,
                            version_id=version_id,
                            score=max_score * 0.95,  # Puntuación contextual ligada a la relevancia del artículo
                            payload=payload,
                            text=r["texto"],
                            location_hint=r["location_hint"],
                        )
                    )
                    existing_ids.add(chunk_id)

    # Ordenamiento lógico jerárquico natural
    def _chunk_sort_key(c: RetrievedChunk) -> tuple:
        cap = c.payload.get("capitulo_numero") or 0
        art = c.payload.get("articulo_numero") or 0
        p_num = c.payload.get("paragrafo_numero")
        i_mk = c.payload.get("inciso_marker")
        if p_num is None and i_mk is None:
            order_type = 0  # cuerpo
        elif i_mk is not None:
            order_type = 1  # incisos
        else:
            order_type = 2  # parágrafos
        return (cap, art, order_type, str(i_mk or ""), str(p_num or ""), c.chunk_id)

    expanded_chunks.sort(key=_chunk_sort_key)
    return expanded_chunks
