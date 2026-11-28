"""CRUD de trazas en SQLite.

La tabla ``traces`` ya es creada por ``corpus.db.init_db()``.
Este módulo sólo añade las funciones de inserción y consulta.
"""
from __future__ import annotations

from pathlib import Path

from normativa.corpus.db import get_connection
from normativa.tracing.models import QueryTrace


def insert_trace(trace: QueryTrace, db_path: str | Path | None = None) -> None:
    """Persiste una traza de consulta en la base de datos."""
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO traces (
                id, created_at, version_id, query, response,
                abstained, retrieved_chunks_json, citations_json,
                abstention_reason, retrieval_ms, generation_ms,
                total_ms, execution_status, error_message, latency_ms,
                query_type, context_chunks_json, authorized_versions_json, diagnostics_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO NOTHING
            """,
            (
                trace.id,
                trace.created_at,
                trace.version_id or "",
                trace.query,
                trace.response,
                1 if trace.abstained else 0,
                trace.retrieved_chunks_json,
                trace.citations_json,
                trace.abstention_reason,
                trace.retrieval_ms,
                trace.generation_ms,
                trace.total_ms,
                trace.execution_status,
                trace.error_message,
                trace.total_ms,
                trace.query_type,
                trace.context_chunks_json,
                trace.authorized_versions_json,
                trace.diagnostics_json,
            ),
        )


def get_trace(trace_id: str, db_path: str | Path | None = None) -> QueryTrace | None:
    """Recupera una traza por su ID."""
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM traces WHERE id = ?", (trace_id,)).fetchone()
    if not row:
        return None
    keys = row.keys()
    return QueryTrace(
        id=row["id"],
        created_at=row["created_at"],
        query=row["query"],
        version_id=row["version_id"] or None,
        retrieved_chunks_json=row["retrieved_chunks_json"],
        response=row["response"],
        citations_json=row["citations_json"] if "citations_json" in keys else "[]",
        abstained=bool(row["abstained"]),
        abstention_reason=row["abstention_reason"],
        retrieval_ms=row["retrieval_ms"] if "retrieval_ms" in keys else 0.0,
        generation_ms=row["generation_ms"] if "generation_ms" in keys else 0.0,
        total_ms=row["total_ms"] if "total_ms" in keys else row["latency_ms"],
        execution_status=row["execution_status"] if "execution_status" in keys else "ok",
        error_message=row["error_message"] if "error_message" in keys else None,
        query_type=row["query_type"] if "query_type" in keys else "normative",
        context_chunks_json=row["context_chunks_json"] if "context_chunks_json" in keys else "[]",
        authorized_versions_json=row["authorized_versions_json"] if "authorized_versions_json" in keys else "[]",
        diagnostics_json=row["diagnostics_json"] if "diagnostics_json" in keys else "{}",
    )
