"""Pruebas deterministas del diagnóstico y del presupuesto."""
from __future__ import annotations

from contextlib import closing
import json

from qdrant_client import QdrantClient

from normativa.config import Settings
from normativa.corpus.db import get_connection
from normativa.generation.providers import GenerationCompletion
from normativa.generation.token_budget import _byte_decoder, _qwen_counter
from scripts.diagnosticar_rag import BASE_PROMPT, automatic_retriever, diagnose, list_chunks, main
from test_etapa3_calidad import _corpus


class FakeProvider:
    provider_name = "double"
    model_name = "ficticio"

    def __init__(self):
        self.calls = []

    def complete(self, request):
        self.calls.append(request)
        answer = {"status": "complete", "answer": "Respuesta de prueba.", "used_chunk_ids": ["REF-1"],
                  "abstention_reason": None, "unanswered_parts": []}
        return GenerationCompletion(json.dumps(answer), 20, 10, "stop")


def test_tokenizador_lee_fusiones_y_no_confunde_bytes_y_tokens():
    alphabet = list(_byte_decoder())
    count = _qwen_counter({
        "tokenizer.ggml.pre": "qwen2", "tokenizer.ggml.model": "gpt2",
        "tokenizer.ggml.tokens": [*alphabet, "ab"], "tokenizer.ggml.merges": ["a b"],
    })
    assert count("abab") == 2
    assert count("ab 22") == 4  # " ab" conserva el espacio cuando existe fusión para 'ab'.
    assert count("á") == len("á".encode()) == 2


def test_diagnostico_falla_declaradamente_si_se_omite_contexto_manual(tmp_path, monkeypatch):
    path = tmp_path / "aislado.db"
    with closing(QdrantClient(":memory:")) as store:
        _corpus(path, store, lambda _: [1.0, 0.0])
    with get_connection(path) as conn:
        conn.execute(
            "INSERT INTO versions (id,document_id,family_id,nombre,status,is_active,created_at,updated_at) "
            "SELECT 'archivada',document_id,family_id,nombre,status,0,created_at,updated_at FROM versions WHERE id='reglas'"
        )
        conn.execute(
            "INSERT INTO chunks (id,version_id,document_id,document_name,articulo_tipo,page_start,page_end,"
            "texto,location_hint,created_at) SELECT 'privado','archivada',document_id,document_name,articulo_tipo,"
            "page_start,page_end,'No autorizado',location_hint,created_at FROM chunks WHERE id='regla'"
        )

    config = Settings(SQLITE_PATH=str(path), RAG_MAX_CONTEXT_CHUNKS=1)
    assert [row["chunk_id"] for row in list_chunks(config, article=73, paragraph="1")] == ["excepcion"]
    assert [row["chunk_id"] for row in list_chunks(config, section="3.2", activity=2)] == ["acuse"]
    assert list_chunks(config, version="archivada") == []
    provider = FakeProvider()
    result = diagnose(config, "¿Cuánto dura la custodia?", chunk_ids=["regla", "excepcion", "privado"],
                      prompt=BASE_PROMPT.read_text(encoding="utf-8"), provider=provider)
    assert len(provider.calls) == 1 and not result["manual_context_complete"]
    assert result["timings_ms"]["retrieval_ms"] == 0
    assert result["discarded"] == {"excepcion": "omitted_by_count", "privado": "no_autorizado_o_inexistente"}
    assert [c["chunk_id"] for c in result["context"]] == ["regla"]
    assert "No autorizado" not in result["generation"]["request"]["messages"][1]["content"]
    assert result["generation"]["request"]["messages"][1]["content"] == provider.calls[0].prompt
    assert result["citations"][0]["chunk_id"] == "regla"
    complete = diagnose(config, "¿Cuánto dura la custodia?", chunk_ids=["regla"], provider=provider)
    assert complete["manual_context_complete"] and complete["manual_missing"] == []
    with get_connection(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM traces").fetchone()[0] == 0

    monkeypatch.setenv("LLM_PROVIDER", "simulated")
    export = tmp_path / "listado.json"
    assert main(["--db", str(path), "--salida", str(export), "listar", "--literal", "g"]) == 0
    assert json.loads(export.read_text())[0]["chunk_id"] == "lista-g"


def test_diagnostico_automatico_informa_limite_de_expansion(tmp_path):
    path = tmp_path / "aislado.db"
    config = Settings(SQLITE_PATH=str(path), RAG_TOP_K=1, RAG_MAX_EXPANDED_CHUNKS=1, QDRANT_COLLECTION="calidad")
    with closing(QdrantClient(":memory:")) as store:
        _corpus(path, store, lambda _: [1.0, 0.0])
        retriever = automatic_retriever(config, client=store, embed_fn=lambda _: [1.0, 0.0])
        result = diagnose(config, "Enumera lo requerido en el artículo 84.", provider=FakeProvider(), retriever=retriever)
    assert result["mode"] == "rag"
    assert result["selection"]["expanded_chunks"] == ["lista-a"]
    assert {f"lista-{letter}" for letter in "bcdefg"} <= set(result["selection"]["omitted_by_expansion"])
    assert all(chunk["incomplete_unit"] for chunk in result["context"])
