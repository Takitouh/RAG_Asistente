"""Servicio RAG de extremo a extremo.

Orquesta: Retriever → Generator → Citations → Trace → Response.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from normativa.generation.citations import Citation, build_citations
from normativa.generation.generator import GenerationResult, NormativeGenerator, _DISCLAIMER
from normativa.retrieval.retriever import NormativeRetriever
from normativa.tracing.db import insert_trace
from normativa.tracing.models import QueryTrace

# Longitud máxima de la consulta (protección básica contra abusos)
_MAX_QUERY_LEN = 1000
_MIN_QUERY_LEN = 3


@dataclass
class RAGResponse:
    """Respuesta estructurada del motor RAG."""

    answer: str
    version_id: str | None
    document_name: str | None
    citations: list[Citation]
    abstained: bool
    abstention_reason: str | None
    disclaimer: str
    trace_id: str
    retrieval_ms: float
    generation_ms: float
    total_ms: float


class RAGService:
    """Servicio principal de consulta RAG.

    Parámetros:
        retriever: instancia de NormativeRetriever (inyectable para tests).
        generator: instancia de NormativeGenerator (inyectable para tests).
        db_path: ruta a la base SQLite (None → usa settings).
    """

    def __init__(
        self,
        retriever: NormativeRetriever | None = None,
        generator: NormativeGenerator | None = None,
        db_path: str | Path | None = None,
    ) -> None:
        self._retriever = retriever or NormativeRetriever(db_path=db_path)
        self._generator = generator or NormativeGenerator()
        self._db_path = db_path

    def query(self, query_text: str) -> RAGResponse:
        """Ejecuta una consulta RAG completa.

        Flujo:
        1. Validar la consulta.
        2. Bloquear la versión activa (en retrieve).
        3. Recuperar chunks.
        4. Verificar condiciones de abstención.
        5. Generar respuesta si no hay abstención.
        6. Construir citas.
        7. Registrar traza.
        8. Devolver RAGResponse.
        """
        t0 = time.perf_counter()
        trace_id = str(uuid.uuid4())

        # --- 1. Validación ---
        query_text = query_text.strip()
        if len(query_text) < _MIN_QUERY_LEN:
            raise ValueError(f"La consulta debe tener al menos {_MIN_QUERY_LEN} caracteres.")
        if len(query_text) > _MAX_QUERY_LEN:
            raise ValueError(f"La consulta no puede superar {_MAX_QUERY_LEN} caracteres.")

        # --- 2 & 3. Recuperación (la versión se bloquea aquí) ---
        retrieval_result = self._retriever.retrieve(query_text)

        citations: list[Citation] = []
        gen_result: GenerationResult | None = None

        if retrieval_result.abstained:
            # --- 4a. Abstención por recuperación ---
            abstained = True
            abstention_reason = retrieval_result.abstention_reason
            answer = f"ABSTENCIÓN: {abstention_reason}"
            generation_ms = 0.0
        else:
            # --- 5. Generación ---
            try:
                gen_result = self._generator.generate(
                    query=query_text,
                    retrieved_chunks=retrieval_result.chunks,
                )
            except RuntimeError as exc:
                # Error en LLM: registrar y propagar
                total_ms = (time.perf_counter() - t0) * 1000
                self._save_trace(
                    trace_id=trace_id,
                    query=query_text,
                    version_id=retrieval_result.version_id,
                    retrieved_chunks_json=json.dumps(
                        [{"chunk_id": c.chunk_id, "score": c.score} for c in retrieval_result.chunks]
                    ),
                    response="",
                    citations=[],
                    abstained=True,
                    abstention_reason=str(exc),
                    retrieval_ms=retrieval_result.retrieval_ms,
                    generation_ms=0.0,
                    total_ms=total_ms,
                    execution_status="error",
                    error_message=str(exc),
                )
                raise

            abstained = gen_result.abstained
            abstention_reason = gen_result.abstention_reason
            answer = gen_result.answer
            generation_ms = gen_result.generation_ms

            # --- 6. Citas verificadas ---
            citations = build_citations(
                retrieved_chunks=retrieval_result.chunks,
                used_chunk_ids=gen_result.used_chunk_ids,
            )

        total_ms = (time.perf_counter() - t0) * 1000

        # --- 7. Traza ---
        retrieved_json = json.dumps(
            [{"chunk_id": c.chunk_id, "score": c.score} for c in retrieval_result.chunks]
        )
        citations_json = json.dumps([c.to_dict() for c in citations])
        exec_status = "abstained" if abstained else "ok"

        self._save_trace(
            trace_id=trace_id,
            query=query_text,
            version_id=retrieval_result.version_id,
            retrieved_chunks_json=retrieved_json,
            response=answer,
            citations=citations,
            abstained=abstained,
            abstention_reason=abstention_reason,
            retrieval_ms=retrieval_result.retrieval_ms,
            generation_ms=generation_ms,
            total_ms=total_ms,
            execution_status=exec_status,
            error_message=None,
        )

        return RAGResponse(
            answer=answer,
            version_id=retrieval_result.version_id,
            document_name=retrieval_result.document_name,
            citations=citations,
            abstained=abstained,
            abstention_reason=abstention_reason,
            disclaimer=_DISCLAIMER,
            trace_id=trace_id,
            retrieval_ms=retrieval_result.retrieval_ms,
            generation_ms=generation_ms,
            total_ms=total_ms,
        )

    def _save_trace(
        self,
        *,
        trace_id: str,
        query: str,
        version_id: str | None,
        retrieved_chunks_json: str,
        response: str,
        citations: list[Citation],
        abstained: bool,
        abstention_reason: str | None,
        retrieval_ms: float,
        generation_ms: float,
        total_ms: float,
        execution_status: str,
        error_message: str | None,
    ) -> None:
        citations_json = json.dumps([c.to_dict() for c in citations])
        trace = QueryTrace(
            id=trace_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            query=query,
            version_id=version_id,
            retrieved_chunks_json=retrieved_chunks_json,
            response=response,
            citations_json=citations_json,
            abstained=abstained,
            abstention_reason=abstention_reason,
            retrieval_ms=retrieval_ms,
            generation_ms=generation_ms,
            total_ms=total_ms,
            execution_status=execution_status,
            error_message=error_message,
        )
        try:
            insert_trace(trace, db_path=self._db_path)
        except Exception:
            # No interrumpir la respuesta al usuario si falla la traza
            pass
