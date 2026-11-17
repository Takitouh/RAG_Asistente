from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class ProcessingStatus(str, Enum):
    RECIBIDO = "RECIBIDO"
    EN_PROCESAMIENTO = "EN_PROCESAMIENTO"
    PENDIENTE_REVISION = "PENDIENTE_REVISION"
    PROCESADO = "PROCESADO"
    ERROR = "ERROR"


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    id: str
    filename: str
    file_path: str
    file_hash: str
    file_size_bytes: int
    uploaded_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NormativeVersion:
    id: str  # version_id
    document_id: str
    nombre: str
    numero_acuerdo: str | None
    anio: int | None
    fecha_expedicion: str | None
    estado_vigencia: str | None
    status: ProcessingStatus
    status_message: str | None
    is_active: bool
    created_at: str
    updated_at: str
    activated_at: str | None = None
    report_json: str | None = None
    chunks_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value if isinstance(self.status, ProcessingStatus) else str(self.status)
        return data


@dataclass(frozen=True, slots=True)
class NormativeChunk:
    chunk_id: str
    version_id: str
    document_id: str
    document_name: str
    capitulo_numero: int | None
    capitulo_romano: str | None
    capitulo_titulo: str | None
    articulo_numero: int | None
    articulo_ordinal: str | None
    articulo_tipo: str
    paragrafo_numero: str | None
    inciso_marker: str | None
    page_start: int
    page_end: int
    texto: str
    ocr_confidence: float | None
    location_hint: str
    extra_metadata: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "version_id": self.version_id,
            "document_id": self.document_id,
            "document_name": self.document_name,
            "capitulo_numero": self.capitulo_numero,
            "capitulo_romano": self.capitulo_romano,
            "capitulo_titulo": self.capitulo_titulo,
            "articulo_numero": self.articulo_numero,
            "articulo_ordinal": self.articulo_ordinal,
            "articulo_tipo": self.articulo_tipo,
            "paragrafo_numero": self.paragrafo_numero,
            "inciso_marker": self.inciso_marker,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "text": self.texto,
            "ocr_confidence": self.ocr_confidence,
            "location_hint": self.location_hint,
            **self.extra_metadata,
        }

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
