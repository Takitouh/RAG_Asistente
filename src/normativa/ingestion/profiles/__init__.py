"""src/normativa/ingestion/profiles/__init__.py

Registro de procesadores de perfil documental.
El administrador puede asociar perfiles existentes a nuevas familias documentales
desde la capa de base de datos (campo perfil_procesamiento en families)
sin modificar este código.
"""
from __future__ import annotations

from normativa.ingestion.profiles.base import BaseProfileProcessor, DocumentProfile, ProfileProcessingResult
from normativa.ingestion.profiles.reglamento import ReglamentoProfileProcessor
from normativa.ingestion.profiles.procedimiento import ProcedimientoProfileProcessor
from normativa.ingestion.profiles.formato import FormatoProfileProcessor
from normativa.ingestion.profiles.general import GeneralProfileProcessor

PROFILE_REGISTRY: dict[DocumentProfile, type[BaseProfileProcessor]] = {
    DocumentProfile.REGLAMENTO_ESTRUCTURADO: ReglamentoProfileProcessor,
    DocumentProfile.PROCEDIMIENTO_INSTITUCIONAL: ProcedimientoProfileProcessor,
    DocumentProfile.FORMATO_INSTITUCIONAL: FormatoProfileProcessor,
    DocumentProfile.DOCUMENTO_GENERAL: GeneralProfileProcessor,
}


def get_processor(profile: DocumentProfile | str) -> BaseProfileProcessor:
    """Devuelve la instancia del procesador para el perfil indicado."""
    if isinstance(profile, str):
        profile = DocumentProfile(profile)
    cls = PROFILE_REGISTRY.get(profile)
    if cls is None:
        raise ValueError(f"Perfil de procesamiento no registrado: '{profile}'")
    return cls()


__all__ = [
    "BaseProfileProcessor",
    "DocumentProfile",
    "ProfileProcessingResult",
    "ReglamentoProfileProcessor",
    "ProcedimientoProfileProcessor",
    "FormatoProfileProcessor",
    "GeneralProfileProcessor",
    "PROFILE_REGISTRY",
    "get_processor",
]
