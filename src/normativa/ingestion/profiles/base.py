"""src/normativa/ingestion/profiles/base.py

Definición de perfiles de procesamiento documental e interfaces base.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from normativa.ingestion.extractor import PageText

if TYPE_CHECKING:
    from normativa.corpus.models import NormativeChunk


class DocumentProfile(str, Enum):
    REGLAMENTO_ESTRUCTURADO = "reglamento_estructurado"
    PROCEDIMIENTO_INSTITUCIONAL = "procedimiento_institucional"
    FORMATO_INSTITUCIONAL = "formato_institucional"
    DOCUMENTO_GENERAL = "documento_general"


@dataclass
class ProfileProcessingResult:
    profile: DocumentProfile
    num_pages: int
    chunks: list[NormativeChunk]
    report: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseProfileProcessor(ABC):
    @property
    @abstractmethod
    def profile(self) -> DocumentProfile:
        ...

    @abstractmethod
    def process(
        self,
        pdf_path: Path,
        pages: list[PageText],
        version_id: str,
        document_id: str,
        document_name: str,
        categoria_id: str | None = None,
        family_id: str | None = None,
        expected_articles_count: int | None = None,
    ) -> ProfileProcessingResult:
        ...
