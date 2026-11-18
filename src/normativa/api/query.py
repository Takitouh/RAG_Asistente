"""Endpoint público de consulta RAG."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from normativa.generation.rag_service import RAGService

query_router = APIRouter(prefix="/api", tags=["Consulta RAG"])


# ---------------------------------------------------------------------------
# Schemas Pydantic
# ---------------------------------------------------------------------------


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000, description="Pregunta en lenguaje natural")


class CitationOut(BaseModel):
    chunk_id: str
    version_id: str
    document_id: str
    document_name: str
    capitulo_numero: int | None = None
    capitulo_romano: str | None = None
    capitulo_titulo: str | None = None
    articulo_numero: int | None = None
    articulo_ordinal: str | None = None
    paragrafo_numero: str | None = None
    inciso_marker: str | None = None
    page_start: int
    page_end: int
    location_hint: str
    texto_fragmento: str


class QueryResponse(BaseModel):
    answer: str
    version_id: str | None
    document_name: str | None
    citations: list[CitationOut]
    abstained: bool
    abstention_reason: str | None
    disclaimer: str
    trace_id: str
    latency_ms: float
    response_type: str = "normative"  # "greeting", "normative", "clarification", "abstention"
    clarification_needed: bool = False
    clarification_question: str | None = None


# ---------------------------------------------------------------------------
# Dependencia del servicio
# ---------------------------------------------------------------------------


def get_rag_service() -> RAGService:
    return RAGService()


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@query_router.post("/query", response_model=QueryResponse)
def query_normativa(
    request: QueryRequest,
    service: RAGService = Depends(get_rag_service),
) -> QueryResponse:
    try:
        result = service.query(request.query)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    citations_out = [CitationOut(**c.to_dict()) for c in result.citations]

    return QueryResponse(
        answer=result.answer,
        version_id=result.version_id,
        document_name=result.document_name,
        citations=citations_out,
        abstained=result.abstained,
        abstention_reason=result.abstention_reason,
        disclaimer=result.disclaimer,
        trace_id=result.trace_id,
        latency_ms=result.total_ms,
        response_type=result.response_type,
        clarification_needed=result.clarification_needed,
        clarification_question=result.clarification_question,
    )
