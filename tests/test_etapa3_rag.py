"""Pruebas aisladas. Solo test_generacion_real_ollama usa modelos reales."""
from __future__ import annotations

import json
import os
from contextlib import closing
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from llama_index.embeddings.ollama import OllamaEmbedding
from qdrant_client import QdrantClient, models

from normativa.api.query import get_rag_service, query_router
from normativa.config import Settings, settings
from normativa.corpus import db
from normativa.generation.generator import NormativeGenerator, ResponseStatus
from normativa.generation.providers import (
    GenerationError, GenerationRequest, GenerationTimeout, OllamaProvider, SimulatedLLMProvider, get_llm_provider,
)
from normativa.generation.rag_service import RAGService
from normativa.retrieval.models import RetrievedChunk
from normativa.retrieval.retriever import NormativeRetriever, _merge_rankings
from normativa.tracing.db import get_trace


def _response(
    chunk_ids: list[str], answer: str, *, status: str = "complete", pending: str | None = None,
) -> str:
    return json.dumps({
        "status": "partial" if pending else status, "answer": answer, "used_chunk_ids": chunk_ids,
        "abstention_reason": None if chunk_ids else "La evidencia no cubre la solicitud.", "unanswered_parts": [pending] if pending else [],
    })


class RecordingProvider(SimulatedLLMProvider):
    def __init__(self, response: str = "", error: Exception | None = None):
        super().__init__(response)
        self.requests: list[GenerationRequest] = []
        self.error = error

    def complete(self, request: GenerationRequest) -> str:
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.response


def _chunks(path: Path, vector_store: QdrantClient, embed) -> None:
    db.init_db(path)
    points = []
    with db.get_connection(path) as conn:
        for version, family, kind, active, chunks in (
            ("antigua", "fam_reglamento_tg", "reglamento_estructurado", 1, [
                ("cuerpo-a", 73, None, "La custodia del prisma dura diecisiete jornadas."),
                ("clausula-a", 73, "1", "La custodia se inicia al registrar la entrega del prisma."),
            ]),
            ("nueva", "fam_reglamento_tg", "reglamento_estructurado", 0, [
                ("cuerpo-n", 94, None, "La custodia del prisma dura cuarenta y tres jornadas."),
                ("clausula-n", 94, "1", "La custodia se inicia al registrar la entrega del prisma."),
            ]),
            ("plantilla", "fam_f_am_04", "formato_institucional", 1, [
                ("forma", None, None, "XZ-LAB-731. Plantilla de registro del prisma."),
            ]),
        ):
            conn.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, 70, '2026-01-01')",
                (version, f"{version}.pdf", f"/tmp/{version}.pdf", version),
            )
            conn.execute(
                """INSERT INTO versions (
                    id, document_id, family_id, nombre, perfil_procesamiento, is_active, estado_revision, status,
                    created_at, updated_at, chunks_count, report_json
                ) VALUES (?, ?, ?, ?, ?, ?, 'APROBADO', 'PROCESADO', '2026-01-01', '2026-01-01', ?, ?)""",
                (version, version, family, version, kind, active, len(chunks), '{"num_pages":2}'),
            )
            for cid, article, paragraph, text in chunks:
                location = f"Artículo {article}" if article else "XZ-LAB-731"
                conn.execute(
                    """INSERT INTO chunks (
                        id, version_id, document_id, document_name, articulo_numero, articulo_tipo, paragrafo_numero,
                        page_start, page_end, texto, location_hint, created_at
                    ) VALUES (?, ?, ?, ?, ?, 'reglamento', ?, 2, 2, ?, ?, '2026-01-01')""",
                    (cid, version, version, f"{version}.pdf", article, paragraph, text, location),
                )
                points.append(models.PointStruct(
                    id=len(points) + 1,
                    vector=embed(text),
                    payload={"chunk_id": cid, "version_id": version, "articulo_numero": article,
                             "articulo_tipo": "reglamento", "location_hint": location, "text": text},
                ))
    vector_store.create_collection(
        "sintetico", vectors_config=models.VectorParams(size=len(points[0].vector), distance=models.Distance.COSINE),
    )
    vector_store.upsert("sintetico", points)


@pytest.fixture
def synthetic(tmp_path):
    path = tmp_path / "sintetico.db"
    with closing(QdrantClient(":memory:")) as vector_store:
        def embed(text: str) -> list[float]:
            if "dura" in text:
                return [1.0, 0.0]
            return [0.8, 0.6] if "custodia" in text else [0.0, 1.0]

        _chunks(path, vector_store, embed)
        yield path, NormativeRetriever(client=vector_store, db_path=path, collection_name="sintetico", embed_fn=embed)


def test_fusion_preserva_prioridad_y_alterna_sin_comparar_scores():
    exact, sem, lex, sem2 = [RetrievedChunk(name, "x", 0.0, {}, name, "") for name in ("e", "s", "l", "s2")]
    assert _merge_rankings([exact], [sem, sem2], [lex, sem, exact]) == [exact, sem, lex, sem2]


def test_busqueda_hibrida_y_expansion_respetan_versiones(synthetic):
    path, retriever = synthetic
    only_first = NormativeRetriever(
        client=retriever._client, db_path=path, collection_name="sintetico",
        embed_fn=lambda _: [1.0, 0.0], top_k=1,
    )
    result = only_first.retrieve("¿Qué dispone el artículo 73?")
    assert result.chunks[0].chunk_id == "cuerpo-a"
    assert any(c.chunk_id == "clausula-a" and c.payload["origin"] == "context_expansion" for c in result.chunks)
    subdivision = only_first.retrieve("¿Qué dispone el parágrafo 1 del artículo 73?")
    assert [c.chunk_id for c in subdivision.chunks] == ["clausula-a", "cuerpo-a"]
    hybrid = NormativeRetriever(
        client=retriever._client, db_path=path, collection_name="sintetico",
        embed_fn=lambda _: [1.0, 0.0], top_k=2,
    )
    result = hybrid.retrieve("¿Qué registra XZ-LAB-731 para el prisma?")
    assert "lexical_search" in {c.payload["origin"] for c in result.candidates}
    assert "semantic" in {c.payload["origin"] for c in result.candidates}
    assert any(c.chunk_id == "forma" for c in result.chunks)
    assert {c.version_id for c in result.chunks} == {"antigua", "plantilla"}


def test_proveedor_configurado_por_defecto_y_simulado():
    default = Settings(_env_file=None, LLM_PROVIDER="ollama", LLM_MODEL="qwen2.5:7b")
    assert get_llm_provider(default).model_name == "qwen2.5:7b"
    assert isinstance(NormativeGenerator(config=Settings(LLM_PROVIDER="simulated")).provider, SimulatedLLMProvider)
    with pytest.raises(GenerationError):
        get_llm_provider(Settings(LLM_PROVIDER="inexistente"))


def test_cambio_de_version_cambia_evidencia_sin_cambiar_codigo(synthetic):
    path, retriever = synthetic
    provider = RecordingProvider(_response(["REF-1"], "Diecisiete jornadas."))
    service = RAGService(db_path=path, retriever=retriever, provider=provider)
    query = "¿Cuánto dura la custodia del prisma?"
    first = service.query(query)
    assert first.status == ResponseStatus.COMPLETE and first.citations[0].articulo_numero == 73
    assert db.activate_version("nueva", path)
    provider.response = _response(["REF-1"], "Cuarenta y tres jornadas.")
    second = service.query(query)
    assert second.status == ResponseStatus.COMPLETE and second.citations[0].articulo_numero == 94
    old_context, new_context = [json.loads(request.prompt)["evidencia"] for request in provider.requests]
    assert any("diecisiete" in item["texto"] for item in old_context)
    assert any("cuarenta y tres" in item["texto"] for item in new_context)
    assert all("diecisiete" not in item["texto"] for item in new_context)
    assert second.citations[0].texto_fragmento == "La custodia del prisma dura cuarenta y tres jornadas."
    trace = get_trace(second.trace_id, path)
    assert trace is not None
    assert {v["id"] for v in json.loads(trace.authorized_versions_json)} == {"nueva", "plantilla"}
    assert [(c["reference"], c["text"]) for c in json.loads(trace.context_chunks_json)] == [
        (item["id"], item["texto"]) for item in new_context
    ]
    assert [c["chunk_id"] for c in json.loads(trace.citations_json)] == ["cuerpo-n"]
    assert len(json.loads(trace.retrieved_chunks_json)) > len(json.loads(trace.citations_json))
    diagnostics = json.loads(trace.diagnostics_json)
    assert diagnostics["provider"] == diagnostics["model"] == "simulated"
    for stage in ("embedding", "semantic", "lexical", "selection", "generation", "validation", "total"):
        assert diagnostics["timings_ms"][f"{stage}_ms"] > 0


@pytest.mark.parametrize(("reply", "status"), [
    (_response(["REF-1"], "Diecisiete jornadas.", pending="No consta el horario."), "partial"),
    (_response([], "", status="out_of_scope"), "out_of_scope"),
    (_response([], "", status="insufficient_evidence"), "insufficient_evidence"),
    (_response(["REF-1", "cuerpo-n"], "Incluir una versión no autorizada."), "insufficient_evidence"),
    (_response(["inventado"], "Referencia inexistente."), "insufficient_evidence"),
    (_response(["REF-1"], "Diecisiete jornadas. Véase REF-1."), "insufficient_evidence"),
    (_response(["REF-1"], "Diecisiete jornadas. Campo used_chunk_ids."), "insufficient_evidence"),
    (_response(["REF-1"], "Diecisiete jornadas (REF-1)."), "complete"),
    (_response(["REF-1"], "Diecisiete jornadas (REF-99)."), "insufficient_evidence"),
    ("Texto libre de un proveedor que no respeta el contrato", "insufficient_evidence"),
])
def test_contrato_parcial_abstenciones_y_citas_invalidas(synthetic, reply, status):
    path, retriever = synthetic
    provider = RecordingProvider(reply)
    result = RAGService(db_path=path, retriever=retriever, provider=provider).query("¿Cuánto dura la custodia del prisma?")
    assert result.status == status
    assert len(provider.requests) == 1
    if status == "partial":
        assert not result.abstained and "No consta el horario." in result.answer
        assert result.unanswered_parts == ["No consta el horario."] and result.clarification_question is None
        assert [c.chunk_id for c in result.citations] == ["cuerpo-a"]
    elif status == "complete":
        assert result.answer == "Diecisiete jornadas."
        assert [c.chunk_id for c in result.citations] == ["cuerpo-a"]
    else:
        assert result.abstained and result.abstention_reason and not result.citations
        assert not result.answered_parts


def test_presupuesto_omite_fragmento_entero_y_rechaza_su_cita(synthetic):
    path, retriever = synthetic
    with db.get_connection(path) as conn:
        conn.execute("UPDATE chunks SET texto = ? WHERE id = 'clausula-a'", ("prisma " * 1500,))
        conn.execute("UPDATE chunks SET page_end = 3 WHERE id = 'forma'")
    provider = RecordingProvider(_response(["clausula-a"], "Cita fuera del contexto."))
    result = RAGService(db_path=path, retriever=retriever, provider=provider).query("¿Cuánto dura la custodia del prisma?")
    request = provider.requests[0]
    context = json.loads(request.prompt)["evidencia"]
    assert [item["texto"] for item in context] == ["La custodia del prisma dura diecisiete jornadas."]
    trace = get_trace(result.trace_id, path)
    diagnostics = json.loads(trace.diagnostics_json)
    assert diagnostics["retrieval"]["omitted_by_budget"] == ["clausula-a"]
    assert diagnostics["retrieval"]["unverified_chunks"] == ["forma"]
    assert result.abstained and not result.citations


@pytest.mark.parametrize("error", [TimeoutError("timeout simulado"), RuntimeError("falla simulada")])
def test_error_tecnico_http_y_traza(synthetic, error):
    path, retriever = synthetic
    provider = RecordingProvider(error=error)
    service = RAGService(db_path=path, retriever=retriever, provider=provider)
    app = FastAPI()
    app.include_router(query_router)
    app.dependency_overrides[get_rag_service] = lambda: service
    response = TestClient(app).post("/api/query", json={"query": "¿Cuánto dura la custodia del prisma?"})
    assert response.status_code == 503
    result = response.json()
    assert result["status"] == "technical_error" and not result["abstained"]
    trace = get_trace(result["trace_id"], path)
    assert trace is not None and trace.execution_status == "error" and trace.generation_ms > 0
    expected = "GenerationTimeout" if isinstance(error, TimeoutError) else "GenerationError"
    assert json.loads(trace.diagnostics_json)["error_type"] == expected
    assert json.loads(trace.context_chunks_json)


def test_ollama_timeout_y_truncamiento(monkeypatch):
    provider = OllamaProvider("qwen2.5:7b", "http://localhost:11434", 1)
    request = GenerationRequest("Sistema", "Consulta", {}, 8192, 1400)

    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("timeout")

    monkeypatch.setattr(httpx, "post", timeout)
    with pytest.raises(GenerationTimeout):
        provider.complete(request)

    def truncated(url, **kwargs):
        assert kwargs["json"]["truncate"] is False
        assert kwargs["json"]["options"]["num_ctx"] == 8192
        assert kwargs["json"]["options"]["num_predict"] == 1400
        return httpx.Response(
            200, request=httpx.Request("POST", url),
            json={"message": {"content": "{}"}, "done": True, "done_reason": "length", "prompt_eval_count": 10, "eval_count": 1400},
        )

    monkeypatch.setattr(httpx, "post", truncated)
    with pytest.raises(GenerationError, match="presupuesto") as exc:
        provider.complete(request)
    assert exc.value.completion.output_tokens == 1400


def test_migracion_de_familias_preserva_nombres_personalizados(tmp_path):
    path = tmp_path / "familias.db"
    db.init_db(path)
    with db.get_connection(path) as conn:
        conn.execute("UPDATE families SET nombre = 'Acta de Inicio de Práctica' WHERE codigo = 'F-DC-127'")
        conn.execute("UPDATE families SET nombre = 'Nombre personalizado' WHERE codigo = 'F-DC-128'")
    db.init_db(path)
    assert db.get_family("fam_f_dc_127", path).nombre == "Propuesta de Trabajo de Grado en Modalidad Práctica"
    assert db.get_family("fam_f_dc_128", path).nombre == "Nombre personalizado"


@pytest.mark.skipif(os.environ.get("RUN_OLLAMA_INTEGRATION") != "1", reason="Requiere Ollama local y modelos instalados")
def test_generacion_real_ollama(tmp_path):
    path = tmp_path / "ollama_sintetico.db"
    embed = OllamaEmbedding(model_name=settings.EMBED_MODEL, base_url=settings.OLLAMA_BASE_URL).get_text_embedding
    config = Settings(LLM_PROVIDER="ollama")
    with closing(QdrantClient(":memory:")) as vector_store:
        _chunks(path, vector_store, embed)
        retriever = NormativeRetriever(client=vector_store, db_path=path, collection_name="sintetico")
        service = RAGService(db_path=path, retriever=retriever, provider=get_llm_provider(config))
        query = "¿Cuántas jornadas dura la custodia del prisma?"
        for version, cid, words, digits in (
            ("antigua", "cuerpo-a", "diecisiete", "17"), ("nueva", "cuerpo-n", "cuarenta y tres", "43"),
        ):
            assert db.activate_version(version, path)
            result = service.query(query)
            trace = get_trace(result.trace_id, path)
            assert result.status == ResponseStatus.COMPLETE, (result, trace)
            assert words in result.answer.lower() or digits in result.answer
            assert cid in {c.chunk_id for c in result.citations}
            assert {c.version_id for c in result.citations} == {version}
            assert json.loads(trace.diagnostics_json)["provider"] == "ollama"
