"""Retrieval package."""
from normativa.retrieval.retriever import NormativeRetriever, RetrievedChunk, RetrievalResult

# QdrantCorpusIndexer se importa de forma diferida para evitar
# la importación circular: indexer → corpus/models → corpus/__init__ → corpus/service → retrieval/indexer
def __getattr__(name: str):
    if name == "QdrantCorpusIndexer":
        from normativa.retrieval.indexer import QdrantCorpusIndexer
        return QdrantCorpusIndexer
    raise AttributeError(f"module 'normativa.retrieval' has no attribute {name!r}")


__all__ = [
    "QdrantCorpusIndexer",
    "NormativeRetriever",
    "RetrievedChunk",
    "RetrievalResult",
]
