"""Modelos de datos para el subsistema de trazabilidad."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from time import perf_counter


@dataclass
class QueryTrace:
    """Traza completa de una consulta RAG."""

    id: str
    created_at: str
    query: str
    version_id: str | None
    retrieved_chunks_json: str   # JSON list[{chunk_id, score}]
    response: str
    citations_json: str          # JSON list[Citation dicts]
    abstained: bool
    abstention_reason: str | None
    retrieval_ms: float
    generation_ms: float
    total_ms: float
    execution_status: str        # "ok" | "error" | "abstained" | "social"
    error_message: str | None = None
    query_type: str = "normative"  # "normative" | "explicit_article" | "greeting" | "clarification"
    context_chunks_json: str = "[]"
    authorized_versions_json: str = "[]"
    diagnostics_json: str = "{}"


@contextmanager
def elapsed(timings: dict[str, float], stage: str) -> Iterator[None]:
    start = perf_counter()
    try:
        yield
    finally:
        timings[stage] = timings.get(stage, 0.0) + (perf_counter() - start) * 1000
