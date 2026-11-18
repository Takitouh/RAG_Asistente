"""Módulo de recuperación normativa híbrida y contextual.

Responsabilidades:
- Identificar la versión activa en el momento de la consulta.
- Detectar referencias normativas explícitas (artículos, parágrafos, acuerdos).
- Generar el embedding de la pregunta usando Ollama (bge-m3).
- Buscar en Qdrant filtrando OBLIGATORIAMENTE por ``version_id``.
- Enriquecer la recuperación con búsqueda léxica y contextual (artículo, cuerpo, incisos).
- Verificar que cada resultado pertenezca a la versión correcta (doble seguro).
- Gestionar la abstención cuando no hay versión activa o no hay resultados relevantes.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llama_index.embeddings.ollama import OllamaEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from normativa.config import settings
from normativa.corpus import db
from normativa.corpus.db import get_active_version
from normativa.retrieval.context_expander import expand_normative_context
from normativa.retrieval.explicit_matcher import fetch_explicit_chunks, match_explicit_reference
from normativa.retrieval.models import RetrievalResult, RetrievedChunk


# ---------------------------------------------------------------------------
# Palabras clave para enriquecimiento léxico en SQLite
# ---------------------------------------------------------------------------
_KEYWORD_PATTERNS = [
    r"\bmodalidad(?:es)?\b",
    r"\bpr[oó]rroga(?:s)?\b",
    r"\binforme\s+final\b",
    r"\bpropuesta(?:s)?\b",
    r"\bcalificaci[oó]n(?:es)?\b",
    r"\breprobaci[oó]n\b",
    r"\bcomit[eé]\b",
    r"\bevaluador(?:es)?\b",
    r"\bdirector(?:es)?\b",
    r"\bseminario\b",
    r"\bmonograf[ií]a\b",
    r"\bpr[aá]ctica\b",
    r"\bemprendimiento\b",
    r"\bderechos?\s+pecuniarios?\b",
    r"\b180\s+d[ií]as\b",
]


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


class NormativeRetriever:
    """Recupera fragmentos normativos de Qdrant y SQLite, aislados por version_id."""

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
    ) -> None:
        self.collection_name = collection_name
        self.top_k = top_k
        self.min_score = min_score
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

    def _lexical_search(self, query: str, version_id: str) -> list[RetrievedChunk]:
        """Búsqueda complementaria por palabras clave en SQLite."""
        matches = []
        for pat in _KEYWORD_PATTERNS:
            if re.search(pat, query, re.IGNORECASE):
                # Extraer raíz de palabra clave
                clean_term = re.sub(r"[^\w\s]", "", pat).replace("\\b", "").strip()
                if clean_term:
                    matches.append(clean_term)

        if not matches:
            return []

        chunks: list[RetrievedChunk] = []
        seen_ids: set[str] = set()

        try:
            with db.get_connection(self.db_path) as conn:
                for term in matches[:2]:  # máximo 2 términos
                    cursor = conn.execute(
                        """
                        SELECT id, version_id, document_id, document_name,
                               capitulo_numero, capitulo_romano, capitulo_titulo,
                               articulo_numero, articulo_ordinal, articulo_tipo,
                               paragrafo_numero, inciso_marker, page_start, page_end,
                               texto, ocr_confidence, location_hint
                        FROM chunks
                        WHERE version_id = ?
                          AND (texto LIKE ? OR location_hint LIKE ?)
                        ORDER BY
                          CASE
                            WHEN paragrafo_numero IS NULL AND inciso_marker IS NULL THEN 0
                            WHEN inciso_marker IS NOT NULL THEN 1
                            ELSE 2
                          END,
                          id
                        LIMIT 5
                        """,
                        (version_id, f"%{term}%", f"%{term}%"),
                    )
                    rows = cursor.fetchall()
                    for r in rows:
                        cid = r["id"]
                        if cid not in seen_ids:
                            seen_ids.add(cid)
                            payload = dict(r)
                            payload["origin"] = "lexical_search"
                            payload["text"] = r["texto"]
                            chunks.append(
                                RetrievedChunk(
                                    chunk_id=cid,
                                    version_id=version_id,
                                    score=0.75,
                                    payload=payload,
                                    text=r["texto"],
                                    location_hint=r["location_hint"],
                                )
                            )
        except Exception:
            pass

        return chunks

    def retrieve(self, query: str) -> RetrievalResult:
        """Ejecuta una búsqueda híbrida y contextual contra la versión activa.

        1. Verifica la versión activa (aislamiento total).
        2. Búsqueda exacta si se menciona un artículo explícito.
        3. Búsqueda vectorial en Qdrant con filtro por version_id.
        4. Búsqueda léxica complementaria en SQLite.
        5. Expansión contextual jerárquica (cuerpo, incisos, parágrafos).
        6. Verificación de seguridad en payload.
        """
        t0 = time.perf_counter()

        # 1. Determinar versión activa
        active = get_active_version(self.db_path)
        if active is None:
            return RetrievalResult(
                version_id=None,
                document_name=None,
                abstained=True,
                abstention_reason="Sin versión activa: no hay ningún reglamento habilitado para consulta.",
                retrieval_ms=(time.perf_counter() - t0) * 1000,
            )

        version_id = active.id
        document_name = active.nombre

        # 2. Búsqueda por referencia explícita (e.g. ¿Qué establece el artículo 15?)
        explicit_chunks: list[RetrievedChunk] = []
        explicit_match = match_explicit_reference(query)
        if explicit_match is not None:
            explicit_chunks = fetch_explicit_chunks(self.db_path, version_id, explicit_match)

        # 3. Búsqueda semántica en Qdrant
        semantic_chunks: list[RetrievedChunk] = []
        try:
            embed_fn = self._get_embed_fn()
            vector = embed_fn(query)
        except Exception as exc:
            raise RuntimeError(f"Error generando embedding para la consulta: {exc}") from exc

        try:
            # Asegurar limit suficiente para candidatos
            search_limit = max(self.top_k, 10)
            results = self._client.query_points(
                collection_name=self.collection_name,
                query=vector,
                query_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="version_id",
                            match=qdrant_models.MatchValue(value=version_id),
                        )
                    ]
                ),
                limit=search_limit,
            )
        except Exception as exc:
            raise RuntimeError(f"Error consultando Qdrant: {exc}") from exc

        for point in results.points:
            payload = point.payload or {}
            if payload.get("version_id") != version_id:
                continue
            score = point.score if hasattr(point, "score") else 0.0
            if score < self.min_score:
                continue
            semantic_chunks.append(
                RetrievedChunk(
                    chunk_id=payload.get("chunk_id", str(point.id)),
                    version_id=version_id,
                    score=score,
                    payload=payload,
                    text=payload.get("text", ""),
                    location_hint=payload.get("location_hint", ""),
                )
            )

        # 4. Búsqueda léxica complementaria
        lexical_chunks = self._lexical_search(query, version_id)

        # 5. Fusión de candidatos priorizando coincidencias explícitas
        combined_chunks: list[RetrievedChunk] = []
        seen_ids: set[str] = set()

        for c in explicit_chunks:
            if c.chunk_id not in seen_ids:
                seen_ids.add(c.chunk_id)
                combined_chunks.append(c)

        for c in semantic_chunks:
            if c.chunk_id not in seen_ids:
                seen_ids.add(c.chunk_id)
                combined_chunks.append(c)

        for c in lexical_chunks:
            if c.chunk_id not in seen_ids:
                seen_ids.add(c.chunk_id)
                combined_chunks.append(c)

        # 6. Expansión contextual jerárquica (conecta parágrafos con cuerpos y recupera incisos)
        final_chunks = expand_normative_context(
            combined_chunks,
            self.db_path,
            version_id,
            query,
        )

        retrieval_ms = (time.perf_counter() - t0) * 1000

        # 7. Evaluación de abstención en recuperación:
        # Si no hay ningún chunk o si el score semántico es extremadamente bajo (< 0.35) sin coincidencias explícitas
        if not final_chunks:
            return RetrievalResult(
                version_id=version_id,
                document_name=document_name,
                abstained=True,
                abstention_reason="No se encontraron fragmentos normativos relevantes para la consulta.",
                retrieval_ms=retrieval_ms,
            )

        max_semantic_score = max((c.score for c in semantic_chunks), default=0.0)
        has_explicit = bool(explicit_chunks)
        if not has_explicit and max_semantic_score < 0.35 and not lexical_chunks:
            return RetrievalResult(
                version_id=version_id,
                document_name=document_name,
                abstained=True,
                abstention_reason="La pregunta está fuera del alcance del reglamento de trabajo de grado.",
                retrieval_ms=retrieval_ms,
            )

        return RetrievalResult(
            version_id=version_id,
            document_name=document_name,
            chunks=final_chunks,
            abstained=False,
            retrieval_ms=retrieval_ms,
        )
