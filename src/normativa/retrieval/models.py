from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
