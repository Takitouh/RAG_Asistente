"""Modelos de datos para el subsistema de trazabilidad."""
from __future__ import annotations

from dataclasses import dataclass, field


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
