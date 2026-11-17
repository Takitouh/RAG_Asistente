from __future__ import annotations

import uuid
from typing import Any, Callable

from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from llama_index.embeddings.ollama import OllamaEmbedding

from normativa.config import settings
from normativa.corpus.models import NormativeChunk


class QdrantCorpusIndexer:
    def __init__(
        self,
        qdrant_url: str = settings.QDRANT_URL,
        collection_name: str = settings.QDRANT_COLLECTION,
        ollama_base_url: str = settings.OLLAMA_BASE_URL,
        embed_model_name: str = settings.EMBED_MODEL,
        client: QdrantClient | None = None,
    ) -> None:
        self.qdrant_url = qdrant_url
        self.collection_name = collection_name
        self.ollama_base_url = ollama_base_url
        self.embed_model_name = embed_model_name
        self._client = client or QdrantClient(url=qdrant_url)
        self._embed_model: OllamaEmbedding | None = None

    def _get_embed_model(self) -> OllamaEmbedding:
        if self._embed_model is None:
            self._embed_model = OllamaEmbedding(
                model_name=self.embed_model_name,
                base_url=self.ollama_base_url,
            )
        return self._embed_model

    def ensure_collection(self, vector_size: int = 1024) -> None:
        collections = self._client.get_collections().collections
        exists = any(col.name == self.collection_name for col in collections)
        if not exists:
            self._client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qdrant_models.VectorParams(
                    size=vector_size,
                    distance=qdrant_models.Distance.COSINE,
                ),
            )
        # Asegurar índice de filtrado para version_id
        try:
            self._client.create_payload_index(
                collection_name=self.collection_name,
                field_name="version_id",
                field_schema=qdrant_models.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            # Índice ya existe o la versión del servidor no lo requiere duplicado
            pass

    @staticmethod
    def generate_point_id(version_id: str, chunk_id: str) -> str:
        """Genera un UUID v5 determinista para evitar colisiones y permitir idempotencia."""
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{version_id}:{chunk_id}"))

    def index_chunks(
        self,
        version_id: str,
        chunks: list[NormativeChunk],
        embed_fn: Callable[[str], list[float]] | None = None,
        batch_size: int = 32,
    ) -> int:
        if not chunks:
            return 0

        self.ensure_collection()

        # Si no se proporciona función de embedding personalizada, se usa Ollama
        if embed_fn is None:
            embedder = self._get_embed_model()
            embed_fn = lambda text: embedder.get_text_embedding(text)

        points: list[qdrant_models.PointStruct] = []
        try:
            for chunk in chunks:
                vector = embed_fn(chunk.texto)
                point_id = self.generate_point_id(version_id, chunk.chunk_id)
                payload = chunk.to_payload()
                points.append(
                    qdrant_models.PointStruct(
                        id=point_id,
                        vector=vector,
                        payload=payload,
                    )
                )

            # Inserción en lotes
            for i in range(0, len(points), batch_size):
                batch = points[i : i + batch_size]
                self._client.upsert(
                    collection_name=self.collection_name,
                    points=batch,
                )

            return len(points)
        except Exception as exc:
            # Rollback: en caso de error, limpiar puntos parciales de esta versión
            try:
                self.delete_version_points(version_id)
            except Exception:
                pass
            raise RuntimeError(f"Error indexando chunks para la versión '{version_id}': {exc}") from exc

    def delete_version_points(self, version_id: str) -> None:
        try:
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="version_id",
                            match=qdrant_models.MatchValue(value=version_id),
                        )
                    ]
                ),
            )
        except Exception:
            # Si la colección no existe aún, ignorar
            pass

    def count_version_points(self, version_id: str) -> int:
        try:
            res = self._client.count(
                collection_name=self.collection_name,
                count_filter=qdrant_models.Filter(
                    must=[
                        qdrant_models.FieldCondition(
                            key="version_id",
                            match=qdrant_models.MatchValue(value=version_id),
                        )
                    ]
                ),
            )
            return res.count
        except Exception:
            return 0
