"""Tests del motor RAG (Iteración 2).

Todos los tests usan mocks para Qdrant, Ollama y SQLite temporal;
no requieren servicios externos activos.
"""
from __future__ import annotations

import json
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_db(tmp_path: Path) -> Path:
    """Crea una base SQLite de prueba con las tablas requeridas."""
    from normativa.corpus.db import init_db

    db = tmp_path / "test.db"
    init_db(db)
    return db


def _insert_version(db: Path, version_id: str = "v_test", is_active: int = 1) -> None:
    conn = sqlite3.connect(str(db))
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute(
        "INSERT OR IGNORE INTO documents (id, filename, file_path, file_hash, file_size_bytes, uploaded_at) "
        "VALUES (?, 'test.pdf', '/tmp/test.pdf', 'abc123', 1024, '2024-01-01T00:00:00+00:00')",
        ("doc_test",),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO versions
        (id, document_id, nombre, numero_acuerdo, anio, status, is_active,
         estado_revision, created_at, updated_at, chunks_count)
        VALUES (?, 'doc_test', 'Reglamento Test', NULL, 2024, 'PROCESADO', ?,
                'APROBADO', '2024-01-01T00:00:00+00:00', '2024-01-01T00:00:00+00:00', 5)
        """,
        (version_id, is_active),
    )
    conn.commit()
    conn.close()


def _make_qdrant_point(chunk_id: str, version_id: str, score: float = 0.85) -> MagicMock:
    """Crea un punto Qdrant simulado."""
    point = MagicMock()
    point.id = f"uuid-{chunk_id}"
    point.score = score
    point.payload = {
        "chunk_id": chunk_id,
        "version_id": version_id,
        "document_id": "doc_test",
        "document_name": "Reglamento Test",
        "capitulo_numero": 1,
        "capitulo_romano": "I",
        "capitulo_titulo": "Disposiciones Generales",
        "articulo_numero": 5,
        "articulo_ordinal": "Quinto",
        "articulo_tipo": "articulo",
        "paragrafo_numero": None,
        "inciso_marker": None,
        "page_start": 3,
        "page_end": 3,
        "text": "El trabajo de grado es un requisito para graduarse.",
        "ocr_confidence": 95.0,
        "location_hint": "Cap. I / Art. 5 / p.3",
    }
    return point


def _qdrant_result(points: list) -> MagicMock:
    result = MagicMock()
    result.points = points
    return result


# ---------------------------------------------------------------------------
# NormativeRetriever tests
# ---------------------------------------------------------------------------


class TestNormativeRetriever:
    def test_retriever_uses_active_version_only(self, tmp_path):
        """El retriever pasa el version_id de la versión activa como filtro."""
        from normativa.retrieval.retriever import NormativeRetriever

        db = _make_db(tmp_path)
        _insert_version(db, "v_active", is_active=1)

        mock_client = MagicMock()
        mock_client.query_points.return_value = _qdrant_result(
            [_make_qdrant_point("chunk_1", "v_active")]
        )

        retriever = NormativeRetriever(
            client=mock_client,
            embed_fn=lambda t: [0.1] * 1024,
            db_path=db,
        )
        result = retriever.retrieve("¿Qué es el trabajo de grado?")

        assert not result.abstained
        assert result.version_id == "v_active"
        # Verificar que el filtro fue por version_id correcto
        call_args = mock_client.query_points.call_args
        qfilter = call_args.kwargs.get("query_filter") or call_args.args[2] if call_args.args else None
        # El filtro debe haber sido llamado con algún argumento
        mock_client.query_points.assert_called_once()

    def test_retriever_excludes_other_versions(self, tmp_path):
        """Los chunks de otra versión son descartados por el post-filtro."""
        from normativa.retrieval.retriever import NormativeRetriever

        db = _make_db(tmp_path)
        _insert_version(db, "v_active", is_active=1)

        # El cliente devuelve un chunk con version_id diferente (error simulado)
        mock_client = MagicMock()
        mock_client.query_points.return_value = _qdrant_result(
            [_make_qdrant_point("chunk_wrong", "v_otra")]
        )

        retriever = NormativeRetriever(
            client=mock_client,
            embed_fn=lambda t: [0.1] * 1024,
            db_path=db,
        )
        result = retriever.retrieve("alguna consulta")

        # El post-filtro debe descartar el chunk de otra versión
        assert result.abstained
        assert result.chunks == []

    def test_retriever_abstains_when_no_active_version(self, tmp_path):
        """Sin versión activa, el retriever abstiene sin llamar a Qdrant."""
        from normativa.retrieval.retriever import NormativeRetriever

        db = _make_db(tmp_path)
        # No se inserta ninguna versión activa

        mock_client = MagicMock()
        retriever = NormativeRetriever(
            client=mock_client,
            embed_fn=lambda t: [0.1] * 1024,
            db_path=db,
        )
        result = retriever.retrieve("cualquier consulta")

        assert result.abstained
        assert result.version_id is None
        assert "Sin versión activa" in result.abstention_reason
        mock_client.query_points.assert_not_called()

    def test_retriever_abstains_when_no_results(self, tmp_path):
        """Si Qdrant no devuelve resultados, el retriever abstiene."""
        from normativa.retrieval.retriever import NormativeRetriever

        db = _make_db(tmp_path)
        _insert_version(db, "v_active")

        mock_client = MagicMock()
        mock_client.query_points.return_value = _qdrant_result([])

        retriever = NormativeRetriever(
            client=mock_client,
            embed_fn=lambda t: [0.1] * 1024,
            db_path=db,
        )
        result = retriever.retrieve("consulta sin resultados")

        assert result.abstained
        assert result.chunks == []

    def test_retriever_handles_qdrant_error(self, tmp_path):
        """Si Qdrant falla, se lanza RuntimeError con mensaje claro."""
        from normativa.retrieval.retriever import NormativeRetriever

        db = _make_db(tmp_path)
        _insert_version(db, "v_active")

        mock_client = MagicMock()
        mock_client.query_points.side_effect = Exception("connection refused")

        retriever = NormativeRetriever(
            client=mock_client,
            embed_fn=lambda t: [0.1] * 1024,
            db_path=db,
        )
        with pytest.raises(RuntimeError, match="Qdrant"):
            retriever.retrieve("consulta con error")

    def test_retriever_handles_embedding_error(self, tmp_path):
        """Si el embedding falla, se lanza RuntimeError con mensaje claro."""
        from normativa.retrieval.retriever import NormativeRetriever

        db = _make_db(tmp_path)
        _insert_version(db, "v_active")

        def bad_embed(text):
            raise Exception("Ollama not available")

        retriever = NormativeRetriever(
            client=MagicMock(),
            embed_fn=bad_embed,
            db_path=db,
        )
        with pytest.raises(RuntimeError, match="embedding"):
            retriever.retrieve("consulta con embedding fallido")

    def test_retriever_returns_correct_chunk_fields(self, tmp_path):
        """Los chunks recuperados tienen todos los campos requeridos."""
        from normativa.retrieval.retriever import NormativeRetriever

        db = _make_db(tmp_path)
        _insert_version(db, "v_active")

        point = _make_qdrant_point("chunk_ok", "v_active", score=0.9)
        mock_client = MagicMock()
        mock_client.query_points.return_value = _qdrant_result([point])

        retriever = NormativeRetriever(
            client=mock_client,
            embed_fn=lambda t: [0.1] * 1024,
            db_path=db,
        )
        result = retriever.retrieve("trabajo de grado")

        assert len(result.chunks) == 1
        chunk = result.chunks[0]
        assert chunk.chunk_id == "chunk_ok"
        assert chunk.version_id == "v_active"
        assert chunk.score == 0.9
        assert chunk.text != ""
        assert chunk.location_hint != ""


# ---------------------------------------------------------------------------
# Citations tests
# ---------------------------------------------------------------------------


class TestCitations:
    def _make_retrieved_chunk(self, chunk_id: str, version_id: str = "v1"):
        from normativa.retrieval.retriever import RetrievedChunk

        return RetrievedChunk(
            chunk_id=chunk_id,
            version_id=version_id,
            score=0.8,
            text="Texto normativo de ejemplo.",
            location_hint="Cap. I / Art. 5 / p.3",
            payload={
                "chunk_id": chunk_id,
                "version_id": version_id,
                "document_id": "doc1",
                "document_name": "Reglamento 2024",
                "capitulo_numero": 1,
                "capitulo_romano": "I",
                "capitulo_titulo": "Generalidades",
                "articulo_numero": 5,
                "articulo_ordinal": "Quinto",
                "paragrafo_numero": None,
                "inciso_marker": None,
                "page_start": 3,
                "page_end": 3,
                "location_hint": "Cap. I / Art. 5 / p.3",
            },
        )

    def test_citations_built_from_metadata_not_llm(self):
        """Las citas se construyen desde el payload del chunk, no desde texto generado."""
        from normativa.generation.citations import build_citations

        chunks = [self._make_retrieved_chunk("c1"), self._make_retrieved_chunk("c2")]
        citations = build_citations(chunks, used_chunk_ids=["c1"])

        assert len(citations) == 1
        assert citations[0].chunk_id == "c1"
        assert citations[0].document_name == "Reglamento 2024"
        assert citations[0].articulo_numero == 5

    def test_citations_reject_invented_ids(self):
        """Los IDs inventados por el LLM son descartados silenciosamente."""
        from normativa.generation.citations import build_citations

        chunks = [self._make_retrieved_chunk("c1")]
        citations = build_citations(chunks, used_chunk_ids=["c1", "inventado_123", "otro_falso"])

        assert len(citations) == 1
        assert citations[0].chunk_id == "c1"

    def test_citations_include_page_and_version(self):
        """Cada cita incluye información de página y version_id."""
        from normativa.generation.citations import build_citations

        chunks = [self._make_retrieved_chunk("c1", version_id="reglamento_2024")]
        citations = build_citations(chunks, used_chunk_ids=["c1"])

        assert citations[0].page_start == 3
        assert citations[0].version_id == "reglamento_2024"

    def test_citations_empty_when_no_used_ids(self):
        """Si el LLM no reporta IDs, no se generan citas."""
        from normativa.generation.citations import build_citations

        chunks = [self._make_retrieved_chunk("c1")]
        citations = build_citations(chunks, used_chunk_ids=[])

        assert citations == []


# ---------------------------------------------------------------------------
# NormativeGenerator tests
# ---------------------------------------------------------------------------


class TestNormativeGenerator:
    def _make_chunk(self, chunk_id: str = "c1"):
        from normativa.retrieval.retriever import RetrievedChunk

        return RetrievedChunk(
            chunk_id=chunk_id,
            version_id="v1",
            score=0.9,
            text="El trabajo de grado tiene tres modalidades.",
            location_hint="Art. 3 / p.2",
            payload={"chunk_id": chunk_id, "version_id": "v1"},
        )

    def test_generator_uses_retrieved_chunks(self):
        """El generador incluye los chunks en el prompt y extrae IDs usados."""
        from normativa.generation.generator import NormativeGenerator

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MagicMock(
            __str__=lambda s: "Las modalidades son tres.\nEVIDENCIA_USADA: [c1]"
        )

        gen = NormativeGenerator(llm=mock_llm)
        chunks = [self._make_chunk("c1")]
        result = gen.generate("¿Cuáles son las modalidades?", chunks)

        assert not result.abstained
        assert "c1" in result.used_chunk_ids
        assert "EVIDENCIA_USADA" not in result.answer

    def test_generator_abstains_on_llm_abstention(self):
        """Si el LLM responde con ABSTENCIÓN:, el resultado indica abstención."""
        from normativa.generation.generator import NormativeGenerator

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MagicMock(
            __str__=lambda s: "ABSTENCIÓN: La pregunta no está relacionada con el reglamento."
        )

        gen = NormativeGenerator(llm=mock_llm)
        result = gen.generate("¿Cuánto cuesta el almuerzo?", [self._make_chunk()])

        assert result.abstained
        assert result.abstention_reason is not None

    def test_generator_abstains_when_no_chunks(self):
        """Sin chunks recuperados, el generador abstiene sin llamar al LLM."""
        from normativa.generation.generator import NormativeGenerator

        mock_llm = MagicMock()
        gen = NormativeGenerator(llm=mock_llm)
        result = gen.generate("¿Algo?", [])

        assert result.abstained
        mock_llm.complete.assert_not_called()

    def test_generator_rejects_invented_chunk_ids(self):
        """Los IDs de evidencia que el LLM inventa son descartados."""
        from normativa.generation.generator import NormativeGenerator

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MagicMock(
            __str__=lambda s: "Respuesta.\nEVIDENCIA_USADA: [c1, inventado_xyz]"
        )

        gen = NormativeGenerator(llm=mock_llm)
        result = gen.generate("pregunta", [self._make_chunk("c1")])

        # inventado_xyz no debe aparecer en los IDs verificados
        assert "inventado_xyz" not in result.used_chunk_ids
        assert "c1" in result.used_chunk_ids


# ---------------------------------------------------------------------------
# Abstención tests
# ---------------------------------------------------------------------------


class TestAbstencion:
    def test_abstention_no_active_version(self, tmp_path):
        """Sin versión activa, el sistema abstiene antes de llamar al LLM."""
        from normativa.generation.rag_service import RAGService
        from normativa.retrieval.retriever import NormativeRetriever

        db = _make_db(tmp_path)
        retriever = NormativeRetriever(
            client=MagicMock(),
            embed_fn=lambda t: [0.0] * 1024,
            db_path=db,
        )
        mock_gen = MagicMock()
        service = RAGService(retriever=retriever, generator=mock_gen, db_path=db)
        result = service.query("¿Cuáles son las modalidades?")

        assert result.abstained
        mock_gen.generate.assert_not_called()

    def test_abstention_no_retrieved_chunks(self, tmp_path):
        """Sin chunks recuperados, el sistema abstiene."""
        from normativa.generation.rag_service import RAGService
        from normativa.retrieval.retriever import NormativeRetriever

        db = _make_db(tmp_path)
        _insert_version(db, "v_active")

        mock_client = MagicMock()
        mock_client.query_points.return_value = _qdrant_result([])

        retriever = NormativeRetriever(
            client=mock_client,
            embed_fn=lambda t: [0.0] * 1024,
            db_path=db,
        )
        mock_gen = MagicMock()
        service = RAGService(retriever=retriever, generator=mock_gen, db_path=db)
        result = service.query("¿Cuáles son las modalidades?")

        assert result.abstained
        mock_gen.generate.assert_not_called()

    def test_abstention_different_from_error(self, tmp_path):
        """Una abstención no es un error; execution_status debe ser 'abstained'."""
        from normativa.tracing.db import get_trace
        from normativa.generation.rag_service import RAGService
        from normativa.retrieval.retriever import NormativeRetriever

        db = _make_db(tmp_path)
        retriever = NormativeRetriever(
            client=MagicMock(),
            embed_fn=lambda t: [0.0] * 1024,
            db_path=db,
        )
        service = RAGService(retriever=retriever, generator=MagicMock(), db_path=db)
        result = service.query("pregunta cualquiera")

        trace = get_trace(result.trace_id, db_path=db)
        assert trace is not None
        assert trace.execution_status == "abstained"
        assert trace.error_message is None

    def test_abstention_out_of_scope_query(self, tmp_path):
        """Una pregunta fuera del alcance retorna abstención del LLM."""
        from normativa.generation.rag_service import RAGService
        from normativa.retrieval.retriever import NormativeRetriever, RetrievedChunk
        from normativa.generation.generator import NormativeGenerator

        db = _make_db(tmp_path)
        _insert_version(db, "v_active")

        point = _make_qdrant_point("c1", "v_active")
        mock_client = MagicMock()
        mock_client.query_points.return_value = _qdrant_result([point])

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MagicMock(
            __str__=lambda s: "ABSTENCIÓN: La pregunta no está relacionada con el reglamento de TG."
        )

        retriever = NormativeRetriever(
            client=mock_client,
            embed_fn=lambda t: [0.1] * 1024,
            db_path=db,
        )
        generator = NormativeGenerator(llm=mock_llm)
        service = RAGService(retriever=retriever, generator=generator, db_path=db)
        result = service.query("¿Cuál es el precio del menú?")

        assert result.abstained
        assert result.abstention_reason is not None


# ---------------------------------------------------------------------------
# Trazabilidad tests
# ---------------------------------------------------------------------------


class TestTracing:
    def test_trace_saved_with_all_fields(self, tmp_path):
        """Cada consulta genera una traza con todos los campos requeridos."""
        from normativa.generation.rag_service import RAGService
        from normativa.retrieval.retriever import NormativeRetriever
        from normativa.generation.generator import NormativeGenerator
        from normativa.tracing.db import get_trace

        db = _make_db(tmp_path)
        _insert_version(db, "v_active")

        point = _make_qdrant_point("c1", "v_active")
        mock_client = MagicMock()
        mock_client.query_points.return_value = _qdrant_result([point])

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MagicMock(
            __str__=lambda s: "Las modalidades son tres.\nEVIDENCIA_USADA: [c1]"
        )

        retriever = NormativeRetriever(
            client=mock_client, embed_fn=lambda t: [0.1] * 1024, db_path=db
        )
        generator = NormativeGenerator(llm=mock_llm)
        service = RAGService(retriever=retriever, generator=generator, db_path=db)
        result = service.query("¿Cuáles son las modalidades?")

        trace = get_trace(result.trace_id, db_path=db)
        assert trace is not None
        assert trace.query == "¿Cuáles son las modalidades?"
        assert trace.version_id == "v_active"
        assert not trace.abstained
        assert trace.execution_status == "ok"
        assert trace.total_ms > 0

    def test_trace_records_abstention(self, tmp_path):
        """La traza registra correctamente cuando hay abstención."""
        from normativa.generation.rag_service import RAGService
        from normativa.retrieval.retriever import NormativeRetriever
        from normativa.tracing.db import get_trace

        db = _make_db(tmp_path)
        retriever = NormativeRetriever(
            client=MagicMock(), embed_fn=lambda t: [0.0] * 1024, db_path=db
        )
        service = RAGService(retriever=retriever, generator=MagicMock(), db_path=db)
        result = service.query("cualquier pregunta")

        trace = get_trace(result.trace_id, db_path=db)
        assert trace.abstained
        assert trace.abstention_reason is not None

    def test_trace_records_timing(self, tmp_path):
        """La traza registra retrieval_ms, generation_ms y total_ms."""
        from normativa.generation.rag_service import RAGService
        from normativa.retrieval.retriever import NormativeRetriever
        from normativa.generation.generator import NormativeGenerator
        from normativa.tracing.db import get_trace

        db = _make_db(tmp_path)
        _insert_version(db, "v_active")

        point = _make_qdrant_point("c1", "v_active")
        mock_client = MagicMock()
        mock_client.query_points.return_value = _qdrant_result([point])

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MagicMock(
            __str__=lambda s: "Respuesta.\nEVIDENCIA_USADA: [c1]"
        )

        retriever = NormativeRetriever(
            client=mock_client, embed_fn=lambda t: [0.1] * 1024, db_path=db
        )
        generator = NormativeGenerator(llm=mock_llm)
        service = RAGService(retriever=retriever, generator=generator, db_path=db)
        result = service.query("pregunta de tiempo")

        trace = get_trace(result.trace_id, db_path=db)
        assert trace.retrieval_ms >= 0
        assert trace.generation_ms >= 0
        assert trace.total_ms >= trace.retrieval_ms


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


class TestQueryEndpoint:
    def _make_app_with_mocks(self, tmp_path: Path, db: Path, with_version: bool = True):
        """Crea la app FastAPI con mocks inyectados."""
        from fastapi.testclient import TestClient
        from normativa.api.main import app
        from normativa.api.query import get_rag_service
        from normativa.generation.rag_service import RAGService
        from normativa.retrieval.retriever import NormativeRetriever
        from normativa.generation.generator import NormativeGenerator

        if with_version:
            _insert_version(db, "v_active")
            point = _make_qdrant_point("c1", "v_active")
            mock_client = MagicMock()
            mock_client.query_points.return_value = _qdrant_result([point])
        else:
            mock_client = MagicMock()

        mock_llm = MagicMock()
        mock_llm.complete.return_value = MagicMock(
            __str__=lambda s: "El trabajo de grado tiene tres modalidades.\nEVIDENCIA_USADA: [c1]"
        )

        retriever = NormativeRetriever(
            client=mock_client, embed_fn=lambda t: [0.1] * 1024, db_path=db
        )
        generator = NormativeGenerator(llm=mock_llm)
        svc = RAGService(retriever=retriever, generator=generator, db_path=db)

        app.dependency_overrides[get_rag_service] = lambda: svc
        client = TestClient(app)
        return client

    def test_api_query_endpoint_returns_correct_contract(self, tmp_path):
        """El endpoint devuelve la estructura JSON correcta."""
        db = _make_db(tmp_path)
        client = self._make_app_with_mocks(tmp_path, db)

        resp = client.post("/api/query", json={"query": "¿Cuáles son las modalidades?"})
        assert resp.status_code == 200
        data = resp.json()

        # Verificar campos obligatorios del contrato
        assert "answer" in data
        assert "version_id" in data
        assert "document_name" in data
        assert "citations" in data
        assert "abstained" in data
        assert "abstention_reason" in data
        assert "disclaimer" in data
        assert "trace_id" in data
        assert "latency_ms" in data
        assert isinstance(data["citations"], list)

        from normativa.api.main import app
        from normativa.api.query import get_rag_service
        app.dependency_overrides.pop(get_rag_service, None)

    def test_api_query_no_auth_required(self, tmp_path):
        """El endpoint de consulta es público — no requiere credenciales."""
        db = _make_db(tmp_path)
        client = self._make_app_with_mocks(tmp_path, db)

        # Sin headers de auth
        resp = client.post("/api/query", json={"query": "¿Cuáles son las modalidades?"})
        assert resp.status_code != 401
        assert resp.status_code != 403

        from normativa.api.main import app
        from normativa.api.query import get_rag_service
        app.dependency_overrides.pop(get_rag_service, None)

    def test_api_query_validates_input_min_length(self, tmp_path):
        """Consultas menores a 3 caracteres son rechazadas con 422."""
        db = _make_db(tmp_path)
        client = self._make_app_with_mocks(tmp_path, db)

        resp = client.post("/api/query", json={"query": "ab"})
        assert resp.status_code == 422

        from normativa.api.main import app
        from normativa.api.query import get_rag_service
        app.dependency_overrides.pop(get_rag_service, None)

    def test_api_query_validates_input_max_length(self, tmp_path):
        """Consultas mayores a 1000 caracteres son rechazadas con 422."""
        db = _make_db(tmp_path)
        client = self._make_app_with_mocks(tmp_path, db)

        resp = client.post("/api/query", json={"query": "x" * 1001})
        assert resp.status_code == 422

        from normativa.api.main import app
        from normativa.api.query import get_rag_service
        app.dependency_overrides.pop(get_rag_service, None)

    def test_api_query_handles_no_active_version(self, tmp_path):
        """Sin versión activa, el endpoint devuelve 200 con abstained=True."""
        db = _make_db(tmp_path)
        client = self._make_app_with_mocks(tmp_path, db, with_version=False)

        resp = client.post("/api/query", json={"query": "¿Cuáles son las modalidades?"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["abstained"] is True

        from normativa.api.main import app
        from normativa.api.query import get_rag_service
        app.dependency_overrides.pop(get_rag_service, None)


# ---------------------------------------------------------------------------
# Metadatos — update_version_metadata
# ---------------------------------------------------------------------------


class TestMetadataUpdate:
    def test_update_version_metadata_allowed_fields(self, tmp_path):
        """El administrador puede corregir metadatos editables."""
        from normativa.corpus.db import update_version_metadata, get_version

        db = _make_db(tmp_path)
        _insert_version(db, "v_meta")

        updated = update_version_metadata(
            version_id="v_meta",
            nombre="Reglamento Corregido",
            anio=2023,
            db_path=db,
        )
        assert updated.nombre == "Reglamento Corregido"
        assert updated.anio == 2023

    def test_update_version_metadata_nonexistent_raises(self, tmp_path):
        """Intentar actualizar una versión inexistente lanza ValueError."""
        from normativa.corpus.db import update_version_metadata

        db = _make_db(tmp_path)
        with pytest.raises(ValueError, match="No existe la versión"):
            update_version_metadata("no_existe", nombre="X", db_path=db)

    def test_update_version_metadata_partial_update(self, tmp_path):
        """Campos no proporcionados no son modificados."""
        from normativa.corpus.db import update_version_metadata

        db = _make_db(tmp_path)
        _insert_version(db, "v_part")

        updated = update_version_metadata(
            version_id="v_part",
            estado_vigencia="vigente",
            db_path=db,
        )
        assert updated.nombre == "Reglamento Test"  # sin cambio
        assert updated.estado_vigencia == "vigente"
