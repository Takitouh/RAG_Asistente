"""Tracing package — trazabilidad de consultas RAG."""
from normativa.tracing.models import QueryTrace
from normativa.tracing.db import insert_trace, get_trace

__all__ = ["QueryTrace", "insert_trace", "get_trace"]
