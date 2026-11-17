"""Generation package — generación de respuestas RAG."""
from normativa.generation.citations import Citation, build_citations
from normativa.generation.generator import NormativeGenerator, GenerationResult
from normativa.generation.rag_service import RAGService, RAGResponse

__all__ = [
    "Citation",
    "build_citations",
    "NormativeGenerator",
    "GenerationResult",
    "RAGService",
    "RAGResponse",
]
