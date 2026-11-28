"""Orquesta recuperación, generación y trazabilidad de la consulta."""
from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from normativa.corpus.db import get_active_versions
from normativa.corpus.models import NormativeVersion, ProcessingStatus
from normativa.generation.citations import Citation, build_citations, load_evidence
from normativa.generation.generator import _DISCLAIMER, NormativeGenerator, ResponseStatus, context_references
from normativa.generation.intents import is_greeting_or_social
from normativa.generation.providers import LLMProvider
from normativa.retrieval.context_expander import structural_unit
from normativa.retrieval.models import RetrievedChunk
from normativa.retrieval.retriever import NormativeRetriever
from normativa.tracing.db import insert_trace
from normativa.tracing.models import QueryTrace, elapsed

_MAX_QUERY_LEN = 1000
_MIN_QUERY_LEN = 3


@dataclass
class RAGResponse:
    answer: str = ""
    version_id: str | None = None
    document_name: str | None = None
    citations: list[Citation] = field(default_factory=list)
    status: ResponseStatus = ResponseStatus.INSUFFICIENT
    abstention_reason: str | None = None
    disclaimer: str = _DISCLAIMER
    trace_id: str = ""
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    total_ms: float = 0.0
    response_type: str = "abstention"
    clarification_question: str | None = None
    authorized_versions: list[str] = field(default_factory=list)
    answered_parts: list[str] = field(default_factory=list)
    unanswered_parts: list[str] = field(default_factory=list)

    @property
    def abstained(self) -> bool:
        return self.status in {ResponseStatus.INSUFFICIENT, ResponseStatus.OUT_OF_SCOPE}

    @property
    def clarification_needed(self) -> bool:
        return bool(self.clarification_question)


def _trace_chunk(chunk: RetrievedChunk) -> dict:
    return {
        "chunk_id": chunk.chunk_id, "version_id": chunk.version_id, "score": chunk.score,
        "location": chunk.location_hint, "origin": chunk.payload.get("origin"),
    }


def authorized_versions(db_path: str | Path | None) -> list[NormativeVersion]:
    return [
        version for version in get_active_versions(db_path)
        if not version.inconsistencia_identidad and version.status == ProcessingStatus.PROCESADO
        and version.estado_revision == "APROBADO"
    ]


class RAGService:
    def __init__(
        self,
        retriever: NormativeRetriever | None = None,
        generator: NormativeGenerator | None = None,
        db_path: str | Path | None = None,
        provider: LLMProvider | None = None,
        trace_sink: Callable[[QueryTrace], None] | None = None,
    ) -> None:
        if generator is not None and provider is not None:
            raise ValueError("Inyecte el generador o el proveedor, según corresponda.")
        self._retriever = retriever or NormativeRetriever(db_path=db_path)
        self._generator = generator or NormativeGenerator(provider=provider)
        self._db_path = db_path
        self._trace_sink = trace_sink

    def query(self, query_text: str) -> RAGResponse:
        start = time.perf_counter()
        query_text = query_text.strip()
        if not _MIN_QUERY_LEN <= len(query_text) <= _MAX_QUERY_LEN:
            raise ValueError(f"La consulta debe tener entre {_MIN_QUERY_LEN} y {_MAX_QUERY_LEN} caracteres.")

        result = RAGResponse(trace_id=str(uuid.uuid4()))
        timings = dict.fromkeys(
            ("embedding_ms", "semantic_ms", "lexical_ms", "selection_ms", "generation_ms", "validation_ms"), 0.0,
        )
        snapshot: list[dict] = []
        candidates: list[RetrievedChunk] = []
        context: list[RetrievedChunk] = []
        incomplete_units: set[tuple] = set()
        retrieval_diagnostics: dict = {}
        generation_diagnostics: dict = {}
        provider_name = model_name = error = error_type = social_type = None
        execution_status = "ok"
        try:
            versions = authorized_versions(self._db_path)
            snapshot = [
                {"id": v.id, "family_id": v.family_id, "nombre": v.nombre, "document_id": v.document_id}
                for v in versions
            ]
            result.authorized_versions = [v.id for v in versions]
            if versions:
                result.version_id, result.document_name = versions[0].id, versions[0].nombre
            social, message, social_type = is_greeting_or_social(query_text, result.document_name)
            if social and message:
                result.answer = message
                result.status = ResponseStatus.SOCIAL
                result.response_type = "greeting"
                execution_status = "social"
            else:
                with elapsed(timings, "retrieval_ms"):
                    retrieval = self._retriever.retrieve(query_text, result.authorized_versions, timings=timings)
                result.version_id, result.document_name = retrieval.version_id, retrieval.document_name
                candidates = retrieval.candidates
                seed_ids = {chunk.chunk_id for chunk in retrieval.seeds}
                retrieval_diagnostics = {
                    "rankings": {
                        name: [_trace_chunk(chunk) for chunk in ranking]
                        for name, ranking in retrieval.rankings.items()
                    },
                    "initial_chunks": [chunk.chunk_id for chunk in retrieval.seeds],
                    "expanded_chunks": [chunk.chunk_id for chunk in retrieval.chunks if chunk.chunk_id not in seed_ids],
                    "omitted_by_expansion": [chunk.chunk_id for chunk in retrieval.omitted_expansion],
                    "outside_initial_limit": [chunk.chunk_id for chunk in candidates if chunk.chunk_id not in seed_ids],
                }
                with elapsed(timings, "selection_ms"):
                    evidence = load_evidence(retrieval.chunks, result.authorized_versions, self._db_path)
                    selection = self._generator.select_context(query_text, evidence) if evidence else None
                    if selection is not None:
                        retrieval_diagnostics.update(
                            omitted_by_count=selection.omitted_by_count,
                            omitted_by_budget=selection.omitted_by_budget,
                            omitted_as_duplicate=selection.omitted_as_duplicate,
                        )
                    verified_ids = {chunk.chunk_id for chunk in evidence}
                    retrieval_diagnostics["unverified_chunks"] = [
                        chunk.chunk_id for chunk in retrieval.chunks if chunk.chunk_id not in verified_ids
                    ]
                if selection is not None and selection.chunks:
                    provider = self._generator.provider
                    provider_name, model_name = provider.provider_name, provider.model_name
                    context = selection.chunks
                    incomplete_units = selection.incomplete_units | {
                        structural_unit(chunk) for chunk in retrieval.omitted_expansion
                    }
                    generated = self._generator.generate(
                        query_text, context, timings, generation_diagnostics, incomplete_units=incomplete_units,
                    )
                    with elapsed(timings, "validation_ms"):
                        result.citations = build_citations(context, generated.used_chunk_ids)
                    result.status = generated.status
                    result.response_type = generated.response_type
                    result.abstention_reason = generated.abstention_reason
                    result.answer = generated.public_answer or "No hay una respuesta sustentada para esta consulta."
                    result.unanswered_parts = generated.unanswered_parts
                else:
                    result.abstention_reason = (
                        retrieval.abstention_reason or "No hay fragmentos verificables dentro del presupuesto de contexto."
                    )
                    result.answer = "No hay evidencia suficiente para responder la consulta."
                if result.abstained:
                    execution_status = "abstained"
        except Exception as exc:
            execution_status = "error"
            error, error_type = str(exc), type(exc).__name__
            result.status = ResponseStatus.TECHNICAL_ERROR
            result.response_type = "error"
            result.answer = "No fue posible completar la consulta por un error técnico."
            result.abstention_reason = None
            result.citations = []

        result.total_ms = (time.perf_counter() - start) * 1000
        result.retrieval_ms = timings.get("retrieval_ms", 0.0)
        result.generation_ms = timings["generation_ms"]
        trace = QueryTrace(
            id=result.trace_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            query=query_text,
            version_id=result.version_id,
            retrieved_chunks_json=json.dumps([_trace_chunk(c) for c in candidates]),
            response=result.answer,
            citations_json=json.dumps([c.to_dict() for c in result.citations]),
            abstained=result.abstained,
            abstention_reason=result.abstention_reason,
            retrieval_ms=result.retrieval_ms,
            generation_ms=result.generation_ms,
            total_ms=result.total_ms,
            execution_status=execution_status,
            error_message=error,
            query_type=(social_type or "greeting") if execution_status == "social" else result.status.value,
            context_chunks_json=json.dumps([
                {**_trace_chunk(chunk), "reference": alias, "text": chunk.text,
                 "document_name": chunk.payload.get("document_name"),
                 "document_profile": chunk.payload.get("perfil_procesamiento"), "literal": chunk.payload.get("inciso_marker"),
                 "incomplete_unit": structural_unit(chunk) in incomplete_units}
                for alias, chunk in context_references(context).items()
            ]),
            authorized_versions_json=json.dumps(snapshot),
            diagnostics_json=json.dumps({
                "provider": provider_name, "model": model_name, "status": result.status,
                "retrieval": retrieval_diagnostics, "generation": generation_diagnostics,
                "timings_ms": {**timings, "total_ms": result.total_ms}, "error_type": error_type,
            }),
        )
        if self._trace_sink is None:
            insert_trace(trace, db_path=self._db_path)
        else:
            self._trace_sink(trace)
        return result
