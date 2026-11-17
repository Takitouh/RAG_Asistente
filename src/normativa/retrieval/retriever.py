"""Módulo de recuperación normativa.

Responsabilidades:
- Identificar la versión activa en el momento de la consulta.
- Generar el embedding de la pregunta usando Ollama (bge-m3).
- Buscar en Qdrant filtrando OBLIGATORIAMENTE por ``version_id``.
- Verificar que cada resultado pertenezca a la versión correcta (doble seguro).
- Gestionar la abstención cuando no hay versión activa o no hay resultados.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from llama_index.embeddings.ollama import OllamaEmbedding
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from normativa.config import settings
from normativa.corpus.db import get_active_version


# ---------------------------------------------------------------------------
# Tipos de datos públicos
# ---------------------------------------------------------------------------


@dataclass
class RetrievedChunk:
    """Un fragmento normativo recuperado con su puntuación de relevancia."""

    chunk_id: str
    version_id: str
    score: float
    payload: dict[str, Any]
    text: str
    location_hint: str


@dataclass
class RetrievalResult:
    """Resultado completo de una operación de recuperación."""

    version_id: str | None
    document_name: str | None
    chunks: list[RetrievedChunk] = field(default_factory=list)
    abstained: bool = False
    abstention_reason: str | None = None
    retrieval_ms: float = 0.0


# ---------------------------------------------------------------------------
# Retriever
# ---------------------------------------------------------------------------


class NormativeRetriever:
    """Recupera fragmentos normativos de Qdrant, aislados por version_id."""

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

    def retrieve(self, query: str) -> RetrievalResult:
        """Ejecuta una búsqueda semántica contra la versión activa.

        La versión activa se determina al inicio de la llamada y se usa como
        filtro obligatorio; nunca se mezclan chunks de distintas versiones.
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

        try:
            # 2. Generar embedding
            embed_fn = self._get_embed_fn()
            vector = embed_fn(query)
        except Exception as exc:
            raise RuntimeError(f"Error generando embedding para la consulta: {exc}") from exc

        try:
            # 3. Buscar en Qdrant con filtro obligatorio por version_id
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
                limit=self.top_k,
            )
        except Exception as exc:
            raise RuntimeError(f"Error consultando Qdrant: {exc}") from exc

        # 4. Post-filtro de seguridad: verificar version_id en payload
        chunks: list[RetrievedChunk] = []
        for point in results.points:
            payload = point.payload or {}
            if payload.get("version_id") != version_id:
                # Chunk de otra versión — ignorar (no debería ocurrir)
                continue
            score = point.score if hasattr(point, "score") else 0.0
            if score < self.min_score:
                continue
            chunks.append(
                RetrievedChunk(
                    chunk_id=payload.get("chunk_id", str(point.id)),
                    version_id=version_id,
                    score=score,
                    payload=payload,
                    text=payload.get("text", ""),
                    location_hint=payload.get("location_hint", ""),
                )
            )

        retrieval_ms = (time.perf_counter() - t0) * 1000

        if not chunks:
            return RetrievalResult(
                version_id=version_id,
                document_name=document_name,
                abstained=True,
                abstention_reason=(
                    "No se encontraron fragmentos normativos relevantes para la consulta."
                ),
                retrieval_ms=retrieval_ms,
            )

        return RetrievalResult(
            version_id=version_id,
            document_name=document_name,
            chunks=chunks,
            abstained=False,
            retrieval_ms=retrieval_ms,
        )
