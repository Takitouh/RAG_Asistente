"""Recuperación semántica, léxica y estructural bajo un snapshot documental."""
from __future__ import annotations

import re
import time
import unicodedata
from itertools import zip_longest
from pathlib import Path

from llama_index.embeddings.ollama import OllamaEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from normativa.config import settings
from normativa.corpus import db
from normativa.corpus.models import ProcessingStatus
from normativa.retrieval.context_expander import expand_normative_context, structural_unit
from normativa.retrieval.explicit_matcher import fetch_explicit_chunks, match_explicit_reference
from normativa.retrieval.models import RetrievalResult, RetrievedChunk
from normativa.tracing.models import elapsed

_IDENTIFIER = re.compile(r"\b[a-z][a-z0-9]*(?:[-_][a-z0-9]+)*[-_]\d+[a-z0-9]*\b")
_STOP_WORDS = frozenset("""
    al algo como con cual cuales cuando cuanto cuantos cuya cuyo donde del desde durante
    ella ellas ellos entre era esa ese eso esta estas este estos hacer hasta hay las los me
    mi mis para pero por porque puedo puede que quien quienes quiere sea segun ser sin son sus
    sobre tengo tiene toda todo tras una unas uno unos usted y
""".split())


def _normalize(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(ch))


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[^\W_]{3,}", text)) - _STOP_WORDS


def _merge_rankings(
    explicit: list[RetrievedChunk], semantic: list[RetrievedChunk], lexical: list[RetrievedChunk],
) -> list[RetrievedChunk]:
    """Prioriza referencias explícitas y alterna los resultados de los dos rankings."""
    candidates: dict[str, RetrievedChunk] = {}
    for chunk in explicit:
        candidates.setdefault(chunk.chunk_id, chunk)
    for pair in zip_longest(semantic, lexical):
        for chunk in pair:
            if chunk is not None:
                candidates.setdefault(chunk.chunk_id, chunk)
    return list(candidates.values())


class NormativeRetriever:
    """Recupera candidatos de Qdrant y SQLite limitados al snapshot de la consulta."""

    def __init__(
        self,
        qdrant_url: str = settings.QDRANT_URL,
        collection_name: str = settings.QDRANT_COLLECTION,
        ollama_base_url: str = settings.OLLAMA_BASE_URL,
        embed_model_name: str = settings.EMBED_MODEL,
        top_k: int = settings.RAG_TOP_K,
        min_score: float = settings.RAG_MIN_SCORE,
        db_path: str | Path | None = None,
        client: QdrantClient | None = None,
        embed_fn=None,  # inyectable para tests
        expansion_units: int = settings.RAG_EXPANSION_UNITS,
        max_expanded_chunks: int | None = settings.RAG_MAX_EXPANDED_CHUNKS,
    ) -> None:
        self.collection_name = collection_name
        self.top_k = top_k
        self.min_score = min_score
        self.expansion_units = expansion_units
        self.max_expanded_chunks = max_expanded_chunks
        self.db_path = db_path
        self._client = client or QdrantClient(url=qdrant_url)
        self._embed_fn = embed_fn
        self._ollama_base_url = ollama_base_url
        self._embed_model_name = embed_model_name
        self._embed_model: OllamaEmbedding | None = None

    def _get_embed_fn(self):
        if self._embed_fn is not None:
            return self._embed_fn
        if self._embed_model is None:
            self._embed_model = OllamaEmbedding(
                model_name=self._embed_model_name,
                base_url=self._ollama_base_url,
            )
        return self._embed_model.get_text_embedding

    def _lexical_search(self, query: str, version_ids: list[str]) -> list[RetrievedChunk]:
        normalized = _normalize(query)
        codes = set(_IDENTIFIER.findall(normalized))
        terms = _terms(_IDENTIFIER.sub(" ", normalized))
        if not (terms or codes):
            return []

        placeholders = ",".join("?" for _ in version_ids)
        ranked: list[tuple[int, int, RetrievedChunk]] = []
        with db.get_connection(self.db_path) as conn:
            rows = conn.execute(
                f"SELECT * FROM chunks WHERE version_id IN ({placeholders}) ORDER BY id", version_ids,
            )
            for row in rows:
                title = _normalize(f"{row['document_name']} {row['location_hint']}")
                text = _normalize(row["texto"])
                code_hits = len(codes.intersection(_IDENTIFIER.findall(f"{title} {text}")))
                overlap = terms & _terms(f"{title} {text}")
                if not (code_hits or overlap):
                    continue
                payload = dict(row)
                payload["origin"] = "lexical_search"
                ranked.append((code_hits, len(overlap), RetrievedChunk(
                    chunk_id=row["id"], version_id=row["version_id"],
                    score=len(overlap) / max(1, len(terms)), payload=payload,
                    text=row["texto"], location_hint=row["location_hint"],
                )))
        ranked.sort(key=lambda hit: (hit[0], hit[1]), reverse=True)
        return [chunk for _, _, chunk in ranked[:self.top_k]]

    def _semantic_search(self, vector: list[float], version_ids: list[str]) -> list[RetrievedChunk]:
        match = (
            qdrant_models.MatchValue(value=version_ids[0])
            if len(version_ids) == 1 else qdrant_models.MatchAny(any=version_ids)
        )
        query_filter = qdrant_models.Filter(must=[qdrant_models.FieldCondition(key="version_id", match=match)])
        try:
            result = self._client.query_points(
                collection_name=self.collection_name,
                query=vector,
                query_filter=query_filter,
                limit=self.top_k,
            )
        except Exception as exc:
            raise RuntimeError("Error consultando Qdrant.") from exc

        chunks: list[RetrievedChunk] = []
        for point in result.points:
            payload = point.payload or {}
            version_id = payload.get("version_id")
            if version_id not in version_ids or point.score < self.min_score:
                continue
            chunks.append(RetrievedChunk(
                chunk_id=payload.get("chunk_id", str(point.id)),
                version_id=version_id, score=point.score,
                payload={**payload, "origin": "semantic"}, text=payload.get("text", ""),
                location_hint=payload.get("location_hint", ""),
            ))
        return sorted(chunks, key=lambda chunk: chunk.score, reverse=True)

    def _context_order(self, seeds: list[RetrievedChunk]) -> list[RetrievedChunk]:
        anchors: dict[tuple, RetrievedChunk] = {}
        for seed in seeds:
            anchors.setdefault(structural_unit(seed), seed)
        # Acercar subdivisiones de las dos unidades de mayor rango. Mantener
        # las demás coincidencias iniciales, sin expandir unidades de menor pertinencia.
        ordered: dict[str, RetrievedChunk] = {}
        remaining: list[list[RetrievedChunk]] = []
        seed_metadata = {seed.chunk_id: seed for seed in seeds}
        for index, seed in enumerate(list(anchors.values())[:self.expansion_units]):
            ordered.setdefault(seed.chunk_id, seed)
            related = [chunk for chunk in expand_normative_context([seed], self.db_path, seed.version_id)
                       if chunk.chunk_id != seed.chunk_id]
            early_count = max(0, 2 - index)
            for chunk in related[:early_count]:
                ordered.setdefault(chunk.chunk_id, seed_metadata.get(chunk.chunk_id, chunk))
            remaining.append(related[early_count:])
        for seed in seeds:
            ordered.setdefault(seed.chunk_id, seed)
        for row in zip_longest(*remaining):
            for chunk in row:
                if chunk is not None:
                    ordered.setdefault(chunk.chunk_id, chunk)
        return list(ordered.values())

    def retrieve(
        self, query: str, authorized_version_ids: list[str] | None = None,
        timings: dict[str, float] | None = None,
    ) -> RetrievalResult:
        if timings is None:
            timings = {}
        start = time.perf_counter()
        if authorized_version_ids is None:
            authorized_version_ids = [v.id for v in db.get_active_versions(self.db_path)
                if not v.inconsistencia_identidad and v.status == ProcessingStatus.PROCESADO
                and v.estado_revision == "APROBADO"]
        if not authorized_version_ids:
            return RetrievalResult(
                None, None, abstained=True,
                abstention_reason="Sin versión activa: no hay ningún reglamento habilitado para consulta.",
                retrieval_ms=(time.perf_counter() - start) * 1000,
            )
        primary = authorized_version_ids[0]
        version = db.get_version(primary, self.db_path) if len(authorized_version_ids) == 1 else None
        document_name = version.nombre if version else f"Corpus activo ({len(authorized_version_ids)} documentos)"

        with elapsed(timings, "embedding_ms"):
            try:
                vector = self._get_embed_fn()(query)
            except Exception as exc:
                raise RuntimeError("Error generando el embedding de la consulta.") from exc
        with elapsed(timings, "semantic_ms"):
            semantic = self._semantic_search(vector, authorized_version_ids)
        with elapsed(timings, "lexical_ms"):
            lexical = self._lexical_search(query, authorized_version_ids)
        with elapsed(timings, "selection_ms"):
            reference = match_explicit_reference(query)
            explicit = [
                chunk for vid in authorized_version_ids
                for chunk in fetch_explicit_chunks(self.db_path, vid, reference)
            ] if reference else []
            ranked = _merge_rankings(explicit, semantic, lexical)
            seeds = ranked[:self.top_k]
            ordered = self._context_order(seeds)
            seed_ids = {seed.chunk_id for seed in seeds}
            added = [chunk for chunk in ordered if chunk.chunk_id not in seed_ids]
            omitted = added[self.max_expanded_chunks:] if self.max_expanded_chunks is not None else []
            omitted_ids = {chunk.chunk_id for chunk in omitted}
            context = [chunk for chunk in ordered if chunk.chunk_id not in omitted_ids]

        return RetrievalResult(
            primary, document_name, chunks=context, candidates=ranked, seeds=seeds,
            rankings={"semantic": semantic, "lexical": lexical, "explicit": explicit}, omitted_expansion=omitted,
            abstained=not context,
            abstention_reason=None if context else "No se encontraron fragmentos pertinentes para la consulta.",
            retrieval_ms=(time.perf_counter() - start) * 1000,
        )
