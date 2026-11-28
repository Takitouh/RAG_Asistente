"""Evaluación con disposiciones ficticias y sin acceso al corpus institucional."""
from __future__ import annotations

from contextlib import closing
import json
import os
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest
from llama_index.embeddings.ollama import OllamaEmbedding
from qdrant_client import QdrantClient, models

from normativa.config import Settings, settings
from normativa.corpus import db
from normativa.generation.generator import NormativeGenerator
from normativa.generation.providers import SimulatedLLMProvider, get_llm_provider
from normativa.generation.rag_service import RAGService
from normativa.retrieval.context_expander import expand_normative_context
from normativa.retrieval.models import RetrievedChunk
from normativa.retrieval.retriever import NormativeRetriever
from normativa.tracing.db import get_trace


# Artículos, actividades, identificadores y valores de un laboratorio ficticio.
_RULES = [
    ("regla", 73, None, None, "Artículo 73", "La custodia del prisma dura 17 jornadas para el grupo Ámbar."),
    ("excepcion", 73, "1", None, "Artículo 73 / Parágrafo 1", "Como excepción, para el grupo Niebla la custodia del prisma dura 4 jornadas."),
    ("recomendacion", 73, "2", None, "Artículo 73 / Parágrafo 2", "Para ambos grupos se recomienda usar una funda violeta durante la custodia. Su uso es voluntario."),
    ("lista", 84, None, None, "Artículo 84", "Para entregar el inventario del prisma deben adjuntarse exactamente todos los elementos enumerados en los literales de este artículo."),
    *[
        (f"lista-{letter}", 84, None, letter, f"Artículo 84 / Literal {letter}",
         f"El inventario del prisma incluye obligatoriamente {label}. " + "Descripción auxiliar del catálogo del laboratorio. " * 11)
        for letter, label in zip("abcdefg", ("un mapa", "una brújula", "una linterna", "una cuerda",
                                          "un sello", "una lupa", "un estuche"), strict=True)
    ],
    ("cierre", 92, None, None, "Artículo 92", "La custodia del prisma finaliza con el registro en el libro de salida."),
]
_PROCEDURES = [
    ("registro", 1, None, None, "QX-91 / 3.2 Entrega del prisma / Actividad 1. Registrar", "La persona custodia registra el prisma en el libro de salida."),
    ("acuse", 2, None, None, "QX-91 / 3.2 Entrega del prisma / Actividad 2. Confirmar", "Una vez asentado el registro, la persona custodia emite un acuse azul para confirmar la entrega del prisma."),
    ("confusor", 2, None, None, "QX-91 / 3.3 Recepción de muestras / Actividad 2. Confirmar", "Para recepción de muestras se emite un acuse naranja."),
]

_CASES = [
    ("condiciones", "¿Cuántas jornadas dura la custodia del prisma para los grupos Ámbar y Niebla y es obligatoria la funda violeta?"),
    ("premisa", "La custodia del prisma para Niebla dura 17 jornadas y exige una funda violeta, ¿es correcto?"),
    ("enumeracion", "Enumera todos los elementos obligatorios del inventario del prisma según el artículo 84."),
    ("complemento", "¿Con qué registro finaliza la custodia del prisma y qué acuse confirma su entrega?"),
    ("parcial", "¿Cuántas jornadas dura la custodia del prisma para Niebla y cuál es el horario de la oficina?"),
]


def _corpus(path: Path, store: QdrantClient, embed, extra_rules=()) -> None:
    db.init_db(path)
    points = []
    with db.get_connection(path) as conn:
        for vid, family, profile, records in (
            ("reglas", "fam_reglamento_tg", "reglamento_estructurado", [*_RULES, *extra_rules]),
            ("operacion", "fam_p_dc_28", "procedimiento_institucional", _PROCEDURES),
        ):
            conn.execute("INSERT INTO documents VALUES (?,?,?,?,70,'2026-01-01')", (vid, vid + ".pdf", "/tmp/" + vid, vid))
            conn.execute(
                """INSERT INTO versions (id, document_id, family_id, nombre, perfil_procesamiento, is_active,
                    estado_revision, status, created_at, updated_at, chunks_count)
                    VALUES (?,?,?,?,?,1,'APROBADO','PROCESADO','2026-01-01','2026-01-01',?)""",
                (vid, vid, family, vid, profile, len(records)),
            )
            kind = "reglamento" if vid == "reglas" else "actividad_procedimiento"
            for cid, article, paragraph, literal, location, body in records:
                conn.execute(
                    """INSERT INTO chunks (id, version_id, document_id, document_name, articulo_numero,
                        articulo_tipo, paragrafo_numero, inciso_marker, page_start, page_end, texto, location_hint, created_at)
                        VALUES (?,?,?,?,?,?,?,?,1,1,?,?,'2026-01-01')""",
                    (cid, vid, vid, vid + ".pdf", article, kind, paragraph, literal, body, location),
                )
                points.append(models.PointStruct(
                    id=len(points) + 1, vector=embed(f"{location}\n{body}"),
                    payload={"chunk_id": cid, "version_id": vid, "articulo_numero": article,
                             "articulo_tipo": kind, "location_hint": location, "text": body,
                             "paragrafo_numero": paragraph, "inciso_marker": literal},
                ))
    store.create_collection("calidad", vectors_config=models.VectorParams(
        size=len(points[0].vector), distance=models.Distance.COSINE,
    ))
    store.upsert("calidad", points)


def measure_quality(path: Path) -> dict:
    """Misma matriz y herramientas para medir previa y posterior a la corrección."""
    embed = OllamaEmbedding(model_name=settings.EMBED_MODEL, base_url=settings.OLLAMA_BASE_URL).get_text_embedding
    post = httpx.post
    measurements = {}
    with closing(QdrantClient(":memory:")) as store:
        _corpus(path, store, embed)
        service = RAGService(
            db_path=path, provider=get_llm_provider(Settings(LLM_PROVIDER="ollama")),
            retriever=NormativeRetriever(client=store, db_path=path, collection_name="calidad", embed_fn=embed),
        )
        for label, query in _CASES:
            usage = {}

            def record(url, **kwargs):
                response = post(url, **kwargs)
                if not url.endswith("/api/chat"):
                    return response
                request = kwargs["json"]
                data = response.json()
                text = "".join(message["content"] for message in request["messages"])
                usage.update(characters=len(text), utf8_bytes=len(text.encode()),
                             input_tokens=data.get("prompt_eval_count"), output_tokens=data.get("eval_count"),
                             done_reason=data.get("done_reason"), raw=json.loads(data["message"]["content"]))
                return response

            with patch("normativa.generation.providers.httpx.post", side_effect=record):
                result = service.query(query)
            trace = get_trace(result.trace_id, path)
            assert trace is not None
            measurements[label] = {
                "status": result.status.value, "answer": result.answer,
                "answered_parts": result.answered_parts, "unanswered_parts": result.unanswered_parts,
                "citations": [c.chunk_id for c in result.citations],
                "context": [chunk["chunk_id"] for chunk in json.loads(trace.context_chunks_json)],
                "candidates": [chunk["chunk_id"] for chunk in json.loads(trace.retrieved_chunks_json)],
                "total_ms": round(result.total_ms), "usage": usage, "diagnostics": json.loads(trace.diagnostics_json),
            }
    return measurements


def test_traza_de_enumeracion_limitada_y_expansion_de_actividades(tmp_path):
    path = tmp_path / "calidad.db"

    def embed(_: str) -> list[float]:
        return [1.0, 0.0]

    with closing(QdrantClient(":memory:")) as store:
        _corpus(path, store, embed)
        retriever = NormativeRetriever(client=store, db_path=path, collection_name="calidad", embed_fn=embed, top_k=1)
        generator = NormativeGenerator(provider=SimulatedLLMProvider(), config=Settings(RAG_MAX_CONTEXT_CHUNKS=2))
        service = RAGService(db_path=path, retriever=retriever, generator=generator)
        result = service.query(_CASES[2][1])
        trace = get_trace(result.trace_id, path)
        diagnostics = json.loads(trace.diagnostics_json)
        selection = diagnostics["retrieval"]
        context = json.loads(trace.context_chunks_json)
        assert selection["initial_chunks"] == ["lista"]
        assert len(selection["rankings"]["semantic"]) == len(selection["rankings"]["lexical"]) == 1
        assert selection["expanded_chunks"] == [f"lista-{letter}" for letter in "abcdefg"]
        assert selection["omitted_by_count"] == [f"lista-{letter}" for letter in "bcdefg"]
        assert selection["omitted_by_budget"] == []
        assert {item["chunk_id"] for item in context} == {"lista", "lista-a"}
        assert all(item["incomplete_unit"] for item in context)
        assert "input_tokens" not in diagnostics["generation"]  # Este proveedor no usa Ollama.

        activity = RetrievedChunk(
            "registro", "operacion", 1.0, {"articulo_numero": 1, "articulo_tipo": "actividad_procedimiento"},
            _PROCEDURES[0][5], _PROCEDURES[0][4],
        )
        neighbors = expand_normative_context([activity], path, "operacion")
        assert [item.chunk_id for item in neighbors] == ["registro", "acuse"]


@pytest.fixture(scope="module")
def real_quality(tmp_path_factory):
    if os.environ.get("RUN_OLLAMA_INTEGRATION") != "1":
        pytest.skip("Requiere Ollama y modelos locales")
    results = measure_quality(tmp_path_factory.mktemp("calidad_ollama") / "calidad.db")
    print("\nMediciones sintéticas con Ollama:")
    for case, result in results.items():
        usage = result["usage"]
        measurements = {key: value for key, value in usage.items() if key != "raw"}
        print(case, result["status"], len(result["context"]), measurements, result["total_ms"], repr(result["answer"]))
    return results


def test_medicion_real_ollama_coincide_con_traza(real_quality):
    for case, result in real_quality.items():
        measured = result["usage"]
        traced = result["diagnostics"]["generation"]
        assert traced["input_tokens"] == measured["input_tokens"] > 0, case
        assert traced["output_tokens"] == measured["output_tokens"] > 0, case
        assert traced["input_utf8_bytes"] == measured["utf8_bytes"], case
        assert traced["estimated_input_tokens"] <= traced["context_window_tokens"] - traced["reserved_output_tokens"], case
        assert traced["input_tokens"] + traced["reserved_output_tokens"] <= traced["context_window_tokens"], case
        assert traced["input_characters"] == measured["characters"], case
        assert measured["done_reason"] == "stop", case
        assert "ref-" not in result["answer"].casefold(), case


@pytest.mark.parametrize("case", [label for label, _ in _CASES])
def test_calidad_generativa_real_ollama(real_quality, case):
    result = real_quality[case]
    answer = result["answer"].casefold()
    citations = set(result["citations"])
    voluntary = ("voluntari", "se recomienda", "no es obligatori", "no obligatori")
    if case == "condiciones":
        assert "17" in answer and "ámbar" in answer and "4" in answer and "niebla" in answer
        assert any(term in answer for term in voluntary)
        assert {"regla", "excepcion", "recomendacion"} <= citations
        assert result["status"] == "complete", result["unanswered_parts"]
    elif case == "premisa":
        assert "4" in answer and any(term in answer for term in voluntary), answer
        assert {"excepcion", "recomendacion"} <= citations
        assert result["status"] == "complete", result["unanswered_parts"]
    elif case == "enumeracion":
        assert all(label in answer for label in ("mapa", "brújula", "linterna", "cuerda", "sello", "lupa", "estuche"))
        assert {f"lista-{letter}" for letter in "abcdefg"} <= citations
        assert result["status"] == "complete"
    elif case == "complemento":
        assert "libro de salida" in answer and "azul" in answer
        assert {"cierre", "acuse"} <= citations
        assert result["status"] == "complete"
    elif case == "parcial":
        assert result["status"] == "partial" and "4" in answer and "horario" in answer, answer
        assert "excepcion" in citations
