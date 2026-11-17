"""Sistema de citas verificables.

Las citas se construyen **exclusivamente** desde los metadatos de los chunks
recuperados por el retriever. El LLM nunca genera citas; sólo indica qué
chunk_ids usó, y el backend verifica que existan en la lista de recuperados.
"""
from __future__ import annotations

from dataclasses import dataclass

from normativa.retrieval.retriever import RetrievedChunk


@dataclass(frozen=True)
class Citation:
    """Referencia verificable a un fragmento del documento original."""

    chunk_id: str
    version_id: str
    document_id: str
    document_name: str
    capitulo_numero: int | None
    capitulo_romano: str | None
    capitulo_titulo: str | None
    articulo_numero: int | None
    articulo_ordinal: str | None
    paragrafo_numero: str | None
    inciso_marker: str | None
    page_start: int
    page_end: int
    location_hint: str
    texto_fragmento: str

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "version_id": self.version_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "capitulo_numero": self.capitulo_numero,
            "capitulo_romano": self.capitulo_romano,
            "capitulo_titulo": self.capitulo_titulo,
            "articulo_numero": self.articulo_numero,
            "articulo_ordinal": self.articulo_ordinal,
            "paragrafo_numero": self.paragrafo_numero,
            "inciso_marker": self.inciso_marker,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "location_hint": self.location_hint,
            "texto_fragmento": self.texto_fragmento[:300],  # preview truncado
        }


def build_citations(
    retrieved_chunks: list[RetrievedChunk],
    used_chunk_ids: list[str],
) -> list[Citation]:
    """Construye citas a partir de los chunks recuperados.

    Solo genera citas para los chunk_ids que:
    1. El LLM indicó haber usado (``used_chunk_ids``).
    2. Existen en la lista de chunks realmente recuperados (``retrieved_chunks``).

    Los IDs inventados por el LLM son silenciosamente descartados.
    """
    chunk_map: dict[str, RetrievedChunk] = {c.chunk_id: c for c in retrieved_chunks}
    citations: list[Citation] = []

    for cid in used_chunk_ids:
        chunk = chunk_map.get(cid)
        if chunk is None:
            # ID inventado o no recuperado — descartado
            continue
        payload = chunk.payload
        citations.append(
            Citation(
                chunk_id=chunk.chunk_id,
                version_id=chunk.version_id,
                document_id=payload.get("document_id", ""),
                document_name=payload.get("document_name", chunk.version_id),
                capitulo_numero=payload.get("capitulo_numero"),
                capitulo_romano=payload.get("capitulo_romano"),
                capitulo_titulo=payload.get("capitulo_titulo"),
                articulo_numero=payload.get("articulo_numero"),
                articulo_ordinal=payload.get("articulo_ordinal"),
                paragrafo_numero=payload.get("paragrafo_numero"),
                inciso_marker=payload.get("inciso_marker"),
                page_start=payload.get("page_start", 0),
                page_end=payload.get("page_end", 0),
                location_hint=chunk.location_hint,
                texto_fragmento=chunk.text,
            )
        )

    return citations
