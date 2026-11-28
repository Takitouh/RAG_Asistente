"""Tests automatizados de regresión para las correcciones del motor RAG.

Verifica los 16 casos mínimos exigidos:
1. Un saludo simple recibe una respuesta cordial.
2. Un saludo no dispara una recuperación innecesaria.
3. Una pregunta sobre modalidades recupera el cuerpo del artículo pertinente.
4. El parágrafo de un artículo puede recuperar su contexto principal.
5. Una consulta explícita sobre un artículo recupera el artículo correcto.
6. Los artículos con números similares no se confunden.
7. Las búsquedas nunca mezclan versiones.
8. Una consulta sobre prórrogas recupera información pertinente.
9. Una consulta ambigua produce aclaración cuando corresponda.
10. La evidencia parcial puede dar lugar a una respuesta parcial fundamentada.
11. Una consulta fuera del dominio produce abstención.
12. Los errores técnicos no se presentan como abstenciones normativas.
13. Las citas proceden de metadatos verificables.
14. No se aceptan citas inventadas.
15. La recuperación contextual no incorpora fragmentos de otra versión.
16. Las modificaciones no rompen los contratos utilizados por React.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from normativa.api.main import app
from normativa.corpus import db
from normativa.corpus.models import DocumentMetadata, NormativeChunk, NormativeVersion, ProcessingStatus
from normativa.generation.generator import GenerationResult, NormativeGenerator
from normativa.generation.intents import is_greeting_or_social
from normativa.generation.rag_service import RAGService
from normativa.retrieval.context_expander import expand_normative_context
from normativa.retrieval.explicit_matcher import fetch_explicit_chunks, match_explicit_reference
from normativa.retrieval.models import RetrievedChunk
from normativa.retrieval.retriever import NormativeRetriever


@pytest.fixture
def test_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "test_rag_fixes.db"
    db.init_db(db_file)

    # Documento y Versión Activa
    doc1 = DocumentMetadata(
        id="doc_2019",
        filename="reglamento_2019.pdf",
        file_path=str(tmp_path / "reglamento_2019.pdf"),
        file_hash="hash2019",
        file_size_bytes=5000,
        uploaded_at="2026-01-01T00:00:00Z",
    )
    db.save_document(doc1, db_file)

    ver1 = NormativeVersion(
        id="v_2019",
        document_id="doc_2019",
        nombre="Reglamento Trabajo de Grado 2019",
        numero_acuerdo="01-001",
        anio=2019,
        fecha_expedicion="2019-01-01",
        estado_vigencia="Vigente",
        status=ProcessingStatus.PROCESADO,
        status_message="Ok",
        is_active=True,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        chunks_count=10,
        estado_revision="APROBADO",
    )
    db.save_version(ver1, db_file)

    # Versión Inactiva (para pruebas de aislamiento)
    doc2 = DocumentMetadata(
        id="doc_2021",
        filename="reglamento_2021.pdf",
        file_path=str(tmp_path / "reglamento_2021.pdf"),
        file_hash="hash2021",
        file_size_bytes=5000,
        uploaded_at="2026-01-02T00:00:00Z",
    )
    db.save_document(doc2, db_file)

    ver2 = NormativeVersion(
        id="v_2021",
        document_id="doc_2021",
        nombre="Reglamento Trabajo de Grado 2021",
        numero_acuerdo="01-002",
        anio=2021,
        fecha_expedicion="2021-01-01",
        estado_vigencia="Inactivo",
        status=ProcessingStatus.PROCESADO,
        status_message="Ok",
        is_active=False,
        created_at="2026-01-02T00:00:00Z",
        updated_at="2026-01-02T00:00:00Z",
        chunks_count=5,
    )
    db.save_version(ver2, db_file)

    # Chunks representativos de v_2019:
    # Artículo 8 (Modalidades): Cuerpo, Incisos y Parágrafo
    chunks_v2019 = [
        NormativeChunk(
            chunk_id="v_2019_art_8_cuerpo",
            version_id="v_2019",
            document_id="doc_2019",
            document_name="reglamento_2019.pdf",
            capitulo_numero=3,
            capitulo_romano="III",
            capitulo_titulo="De las Modalidades",
            articulo_numero=8,
            articulo_ordinal="8°",
            articulo_tipo="reglamento",
            paragrafo_numero=None,
            inciso_marker=None,
            page_start=4,
            page_end=4,
            texto="Capítulo III. Artículo 8: El estudiante puede desarrollar alguna de las siguientes modalidades de Trabajo de Grado:",
            ocr_confidence=95.0,
            location_hint="Capítulo III, Artículo 8",
        ),
        NormativeChunk(
            chunk_id="v_2019_art_8_inc_a",
            version_id="v_2019",
            document_id="doc_2019",
            document_name="reglamento_2019.pdf",
            capitulo_numero=3,
            capitulo_romano="III",
            capitulo_titulo="De las Modalidades",
            articulo_numero=8,
            articulo_ordinal="8°",
            articulo_tipo="reglamento",
            paragrafo_numero=None,
            inciso_marker="a",
            page_start=4,
            page_end=4,
            texto="Capítulo III. Artículo 8, Inciso a): Proyecto de Investigación",
            ocr_confidence=95.0,
            location_hint="Capítulo III, Artículo 8, Inciso a",
        ),
        NormativeChunk(
            chunk_id="v_2019_art_8_inc_b",
            version_id="v_2019",
            document_id="doc_2019",
            document_name="reglamento_2019.pdf",
            capitulo_numero=3,
            capitulo_romano="III",
            capitulo_titulo="De las Modalidades",
            articulo_numero=8,
            articulo_ordinal="8°",
            articulo_tipo="reglamento",
            paragrafo_numero=None,
            inciso_marker="b",
            page_start=4,
            page_end=4,
            texto="Capítulo III. Artículo 8, Inciso b): Práctica Empresarial",
            ocr_confidence=95.0,
            location_hint="Capítulo III, Artículo 8, Inciso b",
        ),
        NormativeChunk(
            chunk_id="v_2019_art_8_par_único",
            version_id="v_2019",
            document_id="doc_2019",
            document_name="reglamento_2019.pdf",
            capitulo_numero=3,
            capitulo_romano="III",
            capitulo_titulo="De las Modalidades",
            articulo_numero=8,
            articulo_ordinal="8°",
            articulo_tipo="reglamento",
            paragrafo_numero="único",
            inciso_marker=None,
            page_start=4,
            page_end=4,
            texto="Capítulo III. Artículo 8, Parágrafo único: El estudiante puede optar por la modalidad aprobada por su programa.",
            ocr_confidence=95.0,
            location_hint="Capítulo III, Artículo 8, Parágrafo único",
        ),
        # Artículo 14 (Plazo y entrega de informe final)
        NormativeChunk(
            chunk_id="v_2019_art_14_cuerpo",
            version_id="v_2019",
            document_id="doc_2019",
            document_name="reglamento_2019.pdf",
            capitulo_numero=4,
            capitulo_romano="IV",
            capitulo_titulo="Procedimientos",
            articulo_numero=14,
            articulo_ordinal="14°",
            articulo_tipo="reglamento",
            paragrafo_numero=None,
            inciso_marker=None,
            page_start=5,
            page_end=5,
            texto="Capítulo IV. Artículo 14: Dispone de un periodo de 180 días calendario para finalizar su trabajo de grado. En Seminario solo el periodo académico.",
            ocr_confidence=95.0,
            location_hint="Capítulo IV, Artículo 14",
        ),
        NormativeChunk(
            chunk_id="v_2019_art_14_par_1",
            version_id="v_2019",
            document_id="doc_2019",
            document_name="reglamento_2019.pdf",
            capitulo_numero=4,
            capitulo_romano="IV",
            capitulo_titulo="Procedimientos",
            articulo_numero=14,
            articulo_ordinal="14°",
            articulo_tipo="reglamento",
            paragrafo_numero="1",
            inciso_marker=None,
            page_start=5,
            page_end=5,
            texto="Capítulo IV. Artículo 14, Parágrafo único: Deben estimar la entrega del informe final antes de los 180 días.",
            ocr_confidence=95.0,
            location_hint="Capítulo IV, Artículo 14, Parágrafo único",
        ),
        # Artículo 15 (Prórrogas)
        NormativeChunk(
            chunk_id="v_2019_art_15_cuerpo",
            version_id="v_2019",
            document_id="doc_2019",
            document_name="reglamento_2019.pdf",
            capitulo_numero=4,
            capitulo_romano="IV",
            capitulo_titulo="Procedimientos",
            articulo_numero=15,
            articulo_ordinal="15°",
            articulo_tipo="reglamento",
            paragrafo_numero=None,
            inciso_marker=None,
            page_start=5,
            page_end=6,
            texto="Capítulo IV. Artículo 15: Derecho a solicitar prórroga ante el Comité por otro periodo igual hasta dos veces sucesivas.",
            ocr_confidence=95.0,
            location_hint="Capítulo IV, Artículo 15",
        ),
        NormativeChunk(
            chunk_id="v_2019_art_15_par_1",
            version_id="v_2019",
            document_id="doc_2019",
            document_name="reglamento_2019.pdf",
            capitulo_numero=4,
            capitulo_romano="IV",
            capitulo_titulo="Procedimientos",
            articulo_numero=15,
            articulo_ordinal="15°",
            articulo_tipo="reglamento",
            paragrafo_numero="1",
            inciso_marker=None,
            page_start=5,
            page_end=6,
            texto="Capítulo IV. Artículo 15, Parágrafo 1: Seminario no tiene prórroga.",
            ocr_confidence=95.0,
            location_hint="Capítulo IV, Artículo 15, Parágrafo 1",
        ),
        NormativeChunk(
            chunk_id="v_2019_art_15_par_3",
            version_id="v_2019",
            document_id="doc_2019",
            document_name="reglamento_2019.pdf",
            capitulo_numero=4,
            capitulo_romano="IV",
            capitulo_titulo="Procedimientos",
            articulo_numero=15,
            articulo_ordinal="15°",
            articulo_tipo="reglamento",
            paragrafo_numero="3",
            inciso_marker=None,
            page_start=5,
            page_end=6,
            texto="Capítulo IV. Artículo 15, Parágrafo 3: Pago previo del derecho pecuniario correspondiente.",
            ocr_confidence=95.0,
            location_hint="Capítulo IV, Artículo 15, Parágrafo 3",
        ),
        # Artículo 150 en otra versión para prueba de falsos positivos
        NormativeChunk(
            chunk_id="v_2019_art_59_cuerpo",
            version_id="v_2019",
            document_id="doc_2019",
            document_name="reglamento_2019.pdf",
            capitulo_numero=10,
            capitulo_romano="X",
            capitulo_titulo="Disposiciones Finales",
            articulo_numero=59,
            articulo_ordinal="59°",
            articulo_tipo="reglamento",
            paragrafo_numero=None,
            inciso_marker=None,
            page_start=15,
            page_end=15,
            texto="Capítulo X. Artículo 59: Vigencia y derogatorias generales.",
            ocr_confidence=95.0,
            location_hint="Capítulo X, Artículo 59",
        ),
    ]
    db.insert_chunks(chunks_v2019, db_file)

    # Chunk de v_2021 (versión inactiva)
    chunk_v2021 = [
        NormativeChunk(
            chunk_id="v_2021_art_15_cuerpo",
            version_id="v_2021",
            document_id="doc_2021",
            document_name="reglamento_2021.pdf",
            capitulo_numero=4,
            capitulo_romano="IV",
            capitulo_titulo="Procedimientos 2021",
            articulo_numero=15,
            articulo_ordinal="15°",
            articulo_tipo="reglamento",
            paragrafo_numero=None,
            inciso_marker=None,
            page_start=6,
            page_end=6,
            texto="Versión 2021 diferente para artículo 15.",
            ocr_confidence=95.0,
            location_hint="Capítulo IV, Artículo 15 v2021",
        )
    ]
    db.insert_chunks(chunk_v2021, db_file)

    return db_file


# ---------------------------------------------------------------------------
# CASOS DE PRUEBA EXIGIDOS
# ---------------------------------------------------------------------------


def test_1_simple_greeting_receives_cordial_response(test_db: Path):
    """1. Un saludo simple recibe una respuesta cordial y orientativa."""
    mock_retriever = MagicMock()
    mock_gen = MagicMock()
    service = RAGService(retriever=mock_retriever, generator=mock_gen, db_path=test_db)

    res = service.query("Hola")
    assert not res.abstained
    assert "¡Hola!" in res.answer
    assert res.response_type == "greeting"
    assert "Modalidades de trabajo de grado" in res.answer


def test_2_simple_greeting_does_not_trigger_unnecessary_retrieval(test_db: Path):
    """2. Un saludo no dispara una recuperación innecesaria en Qdrant/Ollama."""
    mock_retriever = MagicMock()
    mock_gen = MagicMock()
    service = RAGService(retriever=mock_retriever, generator=mock_gen, db_path=test_db)

    res = service.query("¡Buenos días!")
    assert not res.abstained
    # El retriever y el generator NO fueron llamados
    mock_retriever.retrieve.assert_not_called()
    mock_gen.generate.assert_not_called()
    assert res.retrieval_ms == 0.0


def test_3_modalities_query_retrieves_article_body_and_incisos(test_db: Path):
    """3. Una pregunta sobre modalidades recupera el cuerpo del artículo y sus incisos."""
    initial = [
        RetrievedChunk(
            chunk_id="v_2019_art_8_par_único",
            version_id="v_2019",
            score=0.66,
            payload={"articulo_numero": 8, "articulo_tipo": "reglamento"},
            text="Parágrafo único...",
            location_hint="Art 8",
        )
    ]
    expanded = expand_normative_context(initial, test_db, "v_2019", "¿Cuáles son las modalidades?")
    expanded_ids = {c.chunk_id for c in expanded}

    # Debe contener el cuerpo principal y los incisos a y b
    assert "v_2019_art_8_cuerpo" in expanded_ids
    assert "v_2019_art_8_inc_a" in expanded_ids
    assert "v_2019_art_8_inc_b" in expanded_ids


def test_4_paragraph_retrieves_parent_body(test_db: Path):
    """4. El parágrafo de un artículo recupera su contexto principal (cuerpo)."""
    initial = [
        RetrievedChunk(
            chunk_id="v_2019_art_14_par_1",
            version_id="v_2019",
            score=0.68,
            payload={"articulo_numero": 14, "articulo_tipo": "reglamento", "paragrafo_numero": "1"},
            text="Parágrafo 1...",
            location_hint="Art 14 par 1",
        )
    ]
    expanded = expand_normative_context(initial, test_db, "v_2019", "plazo informe final")
    expanded_ids = {c.chunk_id for c in expanded}

    assert "v_2019_art_14_cuerpo" in expanded_ids


def test_5_explicit_article_query_retrieves_correct_article_and_paragraphs(test_db: Path):
    """5. Una consulta explícita sobre un artículo recupera el artículo correcto y sus parágrafos."""
    match = match_explicit_reference("¿Qué establece el artículo 15?")
    assert match is not None
    assert match.articulo_numero == 15

    chunks = fetch_explicit_chunks(test_db, "v_2019", match)
    chunk_ids = [c.chunk_id for c in chunks]

    assert "v_2019_art_15_cuerpo" in chunk_ids
    assert "v_2019_art_15_par_1" in chunk_ids
    assert "v_2019_art_15_par_3" in chunk_ids
    assert all(c.version_id == "v_2019" for c in chunks)


def test_6_similar_numbers_are_not_confused():
    """6. Los artículos con números similares no se confunden (e.g. 15 vs 150 o 5 vs 59)."""
    m15 = match_explicit_reference("artículo 15")
    assert m15.articulo_numero == 15

    m150 = match_explicit_reference("artículo 150")
    assert m150.articulo_numero == 150
    assert m150.articulo_numero != 15

    m5 = match_explicit_reference("art. 5")
    assert m5.articulo_numero == 5

    m59 = match_explicit_reference("art. 59")
    assert m59.articulo_numero == 59
    assert m59.articulo_numero != 5


def test_7_retrieval_never_mixes_versions(test_db: Path):
    """7. Las búsquedas nunca mezclan versiones (v_2021 inactiva excluida)."""
    match = match_explicit_reference("artículo 15")
    chunks = fetch_explicit_chunks(test_db, "v_2019", match)

    # Debe contener solo v_2019, nunca v_2021
    for c in chunks:
        assert c.version_id == "v_2019"
        assert "v_2021" not in c.chunk_id


def test_8_prorroga_query_retrieves_pertinent_info(test_db: Path):
    """8. Una consulta sobre prórrogas recupera información pertinente de artículo 15."""
    mock_client = MagicMock()
    # Simula que Qdrant devuelve art_15_cuerpo
    point = MagicMock()
    point.id = "uuid-15"
    point.score = 0.65
    point.payload = {
        "chunk_id": "v_2019_art_15_cuerpo",
        "version_id": "v_2019",
        "articulo_numero": 15,
        "articulo_tipo": "reglamento",
        "text": "Derecho a solicitar prórroga...",
        "location_hint": "Art 15",
    }
    mock_client.query_points.return_value = MagicMock(points=[point])

    retriever = NormativeRetriever(
        client=mock_client,
        embed_fn=lambda t: [0.1] * 1024,
        db_path=test_db,
    )
    result = retriever.retrieve("¿Qué sucede si necesito una prórroga?")
    assert not result.abstained
    chunk_ids = {c.chunk_id for c in result.chunks}
    # Por expansión contextual, debe traer además parágrafos 1 y 3
    assert "v_2019_art_15_cuerpo" in chunk_ids
    assert "v_2019_art_15_par_1" in chunk_ids
    assert "v_2019_art_15_par_3" in chunk_ids


def test_9_ambiguous_query_produces_clarification(test_db: Path):
    """9. Una consulta ambigua produce una solicitud de aclaración sin abstención indebida."""
    mock_llm = MagicMock()
    mock_llm.complete.return_value = MagicMock(
        __str__=lambda s: (
            "El reglamento establece un plazo general de 180 días calendario para la finalización del trabajo de grado "
            "(Artículo 14), pero si estás en la modalidad de Seminario el plazo corresponde únicamente al periodo académico. "
            "¿Podrías indicarnos cuál es tu modalidad de trabajo de grado para darte el dato exacto?\n"
            "EVIDENCIA_USADA: [v_2019_art_14_cuerpo]"
        )
    )
    generator = NormativeGenerator(llm=mock_llm)
    chunks = [
        RetrievedChunk(
            chunk_id="v_2019_art_14_cuerpo",
            version_id="v_2019",
            score=0.8,
            payload={"articulo_numero": 14},
            text="180 días...",
            location_hint="Art 14",
        )
    ]
    res = generator.generate("¿Cuántos días tengo para desarrollar mi informe final?", chunks)
    assert not res.abstained
    assert res.clarification_needed
    assert res.response_type == "clarification"


def test_10_partial_evidence_gives_grounded_partial_response():
    """10. La evidencia parcial produce una respuesta fundamentada con advertencia de lo no cubierto."""
    mock_llm = MagicMock()
    mock_llm.complete.return_value = MagicMock(
        __str__=lambda s: (
            "De acuerdo con el Artículo 15, la persona natural tiene derecho a solicitar prórroga por otro periodo igual "
            "hasta en dos ocasiones sucesivas. Sin embargo, el texto no detalla el formato de carta requerido.\n"
            "EVIDENCIA_USADA: [v_2019_art_15_cuerpo]"
        )
    )
    generator = NormativeGenerator(llm=mock_llm)
    chunks = [
        RetrievedChunk(
            chunk_id="v_2019_art_15_cuerpo",
            version_id="v_2019",
            score=0.8,
            payload={"articulo_numero": 15},
            text="Prórroga por otro periodo igual...",
            location_hint="Art 15",
        )
    ]
    res = generator.generate("¿Cómo solicito una prórroga?", chunks)
    assert not res.abstained
    assert "hasta en dos ocasiones sucesivas" in res.answer
    assert "v_2019_art_15_cuerpo" in res.used_chunk_ids


def test_11_out_of_domain_query_produces_abstention(test_db: Path):
    """11. Una consulta fuera del dominio produce abstención."""
    mock_client = MagicMock()
    # Simula puntuaciones muy bajas (< 0.35)
    point = MagicMock()
    point.id = "uuid-low"
    point.score = 0.28
    point.payload = {"chunk_id": "v_2019_art_59_cuerpo", "version_id": "v_2019", "text": "Disposiciones..."}
    mock_client.query_points.return_value = MagicMock(points=[point])

    retriever = NormativeRetriever(
        client=mock_client,
        embed_fn=lambda t: [0.1] * 1024,
        db_path=test_db,
    )
    res = retriever.retrieve("¿Cuál es el precio de una hamburguesa?")
    assert res.abstained
    assert "fuera del alcance" in res.abstention_reason.lower()


def test_12_technical_errors_not_presented_as_abstentions(test_db: Path):
    """12. Los errores técnicos de conexión lanzan RuntimeError y no se disfrazan de abstención."""
    mock_client = MagicMock()
    mock_client.query_points.side_effect = RuntimeError("Conexión rechazada con Qdrant")

    retriever = NormativeRetriever(
        client=mock_client,
        embed_fn=lambda t: [0.1] * 1024,
        db_path=test_db,
    )
    with pytest.raises(RuntimeError) as exc_info:
        retriever.retrieve("¿Cuáles son las modalidades?")
    assert "Qdrant" in str(exc_info.value)


def test_13_citations_from_verifiable_metadata(test_db: Path):
    """13. Las citas proceden de metadatos verificables de los chunks recuperados."""
    from normativa.generation.citations import build_citations

    chunks = [
        RetrievedChunk(
            chunk_id="v_2019_art_8_cuerpo",
            version_id="v_2019",
            score=0.9,
            payload={
                "document_id": "doc_2019",
                "document_name": "reglamento_2019.pdf",
                "capitulo_numero": 3,
                "capitulo_romano": "III",
                "capitulo_titulo": "Modalidades",
                "articulo_numero": 8,
                "page_start": 4,
                "page_end": 4,
            },
            text="Modalidades...",
            location_hint="Art 8",
        )
    ]
    citations = build_citations(chunks, ["v_2019_art_8_cuerpo"])
    assert len(citations) == 1
    assert citations[0].articulo_numero == 8
    assert citations[0].document_name == "reglamento_2019.pdf"
    assert citations[0].page_start == 4


def test_14_invented_citations_rejected():
    """14. No se aceptan citas con IDs inventados por el LLM."""
    from normativa.generation.citations import build_citations

    chunks = [
        RetrievedChunk(
            chunk_id="v_2019_art_8_cuerpo",
            version_id="v_2019",
            score=0.9,
            payload={"articulo_numero": 8},
            text="Modalidades...",
            location_hint="Art 8",
        )
    ]
    citations = build_citations(chunks, ["id_inventado_999"])
    assert len(citations) == 0


def test_15_contextual_expansion_never_incorporates_other_version(test_db: Path):
    """15. La recuperación contextual no incorpora fragmentos de otra versión."""
    initial = [
        RetrievedChunk(
            chunk_id="v_2019_art_15_cuerpo",
            version_id="v_2019",
            score=0.7,
            payload={"articulo_numero": 15, "articulo_tipo": "reglamento"},
            text="Art 15...",
            location_hint="Art 15",
        )
    ]
    expanded = expand_normative_context(initial, test_db, "v_2019", "prórroga")
    for c in expanded:
        assert c.version_id == "v_2019"
        assert "v_2021" not in c.chunk_id


def test_16_contracts_remain_compatible_with_react(test_db: Path):
    """16. El endpoint /api/query conserva y amplía el contrato esperado por React."""
    from normativa.api.admin import get_corpus_service
    from normativa.corpus.service import CorpusService

    service = CorpusService(db_path=test_db)
    app.dependency_overrides[get_corpus_service] = lambda: service

    with TestClient(app) as client:
        # Prueba con saludo
        res = client.post("/api/query", json={"query": "Hola"})
        assert res.status_code == 200
        data = res.json()
        assert "answer" in data
        assert "citations" in data
        assert "abstained" in data
        assert "response_type" in data
        assert "clarification_needed" in data
        assert data["response_type"] == "greeting"
        assert not data["abstained"]

    app.dependency_overrides.clear()
