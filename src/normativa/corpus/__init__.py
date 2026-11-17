"""Corpus package for document, version, and chunk management."""

from normativa.corpus.chunker import build_chunks_from_parsed_document
from normativa.corpus.db import (
    activate_version,
    deactivate_version,
    get_active_version,
    get_chunks_by_version,
    get_document,
    get_version,
    init_db,
    insert_chunks,
    list_documents,
    list_versions,
    save_document,
    save_version,
)
from normativa.corpus.models import (
    DocumentMetadata,
    NormativeChunk,
    NormativeVersion,
    ProcessingStatus,
)
from normativa.corpus.service import CorpusService

__all__ = [
    "CorpusService",
    "DocumentMetadata",
    "NormativeChunk",
    "NormativeVersion",
    "ProcessingStatus",
    "activate_version",
    "build_chunks_from_parsed_document",
    "deactivate_version",
    "get_active_version",
    "get_chunks_by_version",
    "get_document",
    "get_version",
    "init_db",
    "insert_chunks",
    "list_documents",
    "list_versions",
    "save_document",
    "save_version",
]
