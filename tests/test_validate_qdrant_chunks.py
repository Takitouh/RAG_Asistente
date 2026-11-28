"""Pruebas automatizadas para scripts/validate_qdrant_chunks.py."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from normativa.corpus import db
from normativa.corpus.models import DocumentCategory, DocumentFamily, DocumentMetadata, NormativeVersion, ProcessingStatus
from scripts.validate_qdrant_chunks import validate_correspondence


@pytest.fixture
def test_db_for_validator(tmp_path: Path):
    db_file = tmp_path / "test_validator.db"
    db.init_db(db_file)

    cat = DocumentCategory(id="cat_reglamentos", nombre="Reglamentos", descripcion="Test", estado="ACTIVO")
    fam = DocumentFamily(id="fam_reglamento_tg", categoria_id="cat_reglamentos", codigo="RTG", nombre="Reglamento TG", descripcion="Test", estado="ACTIVO")
    db.create_category(cat, db_file)
    db.create_family(fam, db_file)

    doc = DocumentMetadata(
        id="doc_val_001",
        filename="reglamento.pdf",
        file_path="/tmp/reg.pdf",
        file_hash="hash_val_001",
        file_size_bytes=1000,
        uploaded_at="2026-11-27T00:00:00",
    )
    db.save_document(doc, db_file)

    ver = NormativeVersion(
        id="ver_val_001",
        document_id="doc_val_001",
        nombre="Reglamento 2019",
        numero_acuerdo="01",
        anio=2019,
        fecha_expedicion="2019-01-01",
        estado_vigencia="VIGENTE",
        status=ProcessingStatus.PROCESADO,
        status_message="OK",
        is_active=True,
        created_at="2026-11-27T00:00:00",
        updated_at="2026-11-27T00:00:00",
        family_id="fam_reglamento_tg",
        estado_revision="APROBADO",
    )
    db.create_version(ver, db_file)

    conn = sqlite3.connect(str(db_file))
    conn.execute(
        """
        INSERT INTO chunks (
            id, version_id, document_id, document_name, capitulo_numero,
            articulo_numero, articulo_tipo, page_start, page_end, texto,
            location_hint, created_at, family_id, categoria_id
        ) VALUES
        ('c_1', 'ver_val_001', 'doc_val_001', 'reglamento.pdf', 1, 1, 'ARTICULO', 1, 1, 'Texto legal artículo 1', 'Art 1', '2026-11-27', 'fam_reglamento_tg', 'cat_reglamentos'),
        ('c_2', 'ver_val_001', 'doc_val_001', 'reglamento.pdf', 1, 2, 'ARTICULO', 1, 1, 'Texto legal artículo 2', 'Art 2', '2026-11-27', 'fam_reglamento_tg', 'cat_reglamentos')
        """
    )
    conn.commit()
    conn.close()

    return db_file


def _mock_point(point_id: str, chunk_id: str, version_id="ver_val_001", doc_id="doc_val_001", family_id="fam_reglamento_tg", categoria_id="cat_reglamentos", text="Texto legal artículo 1"):
    p = MagicMock()
    p.id = point_id
    p.payload = {
        "chunk_id": chunk_id,
        "version_id": version_id,
        "document_id": doc_id,
        "family_id": family_id,
        "categoria_id": categoria_id,
        "text": text,
        "location_hint": f"Art {chunk_id[-1]}",
    }
    return p


def test_validator_success_on_perfect_match(test_db_for_validator: Path):
    mock_client = MagicMock()
    coll = MagicMock()
    coll.name = "normativa"
    mock_client.get_collections.return_value.collections = [coll]

    points = [
        _mock_point("p1", "c_1", text="Texto legal artículo 1"),
        _mock_point("p2", "c_2", text="Texto legal artículo 2"),
    ]
    mock_client.scroll.return_value = (points, None)

    exit_code, metrics = validate_correspondence(
        collection_name="normativa",
        db_path=test_db_for_validator,
        client=mock_client,
    )

    assert exit_code == 0
    assert metrics["total_discrepancies"] == 0
    assert metrics["orphans"] == 0
    assert metrics["missing_in_qdrant"] == 0
    assert metrics["text_mismatches"] == 0


def test_validator_fails_on_orphan_point(test_db_for_validator: Path):
    mock_client = MagicMock()
    coll = MagicMock()
    coll.name = "normativa"
    mock_client.get_collections.return_value.collections = [coll]

    points = [
        _mock_point("p1", "c_1", text="Texto legal artículo 1"),
        _mock_point("p2", "c_2", text="Texto legal artículo 2"),
        _mock_point("p_orphan", "c_inexistente", text="Fantasma"),
    ]
    mock_client.scroll.return_value = (points, None)

    exit_code, metrics = validate_correspondence(
        collection_name="normativa",
        db_path=test_db_for_validator,
        client=mock_client,
    )

    assert exit_code == 1
    assert metrics["orphans"] == 1
    assert metrics["total_discrepancies"] >= 1


def test_validator_fails_on_missing_point_in_qdrant(test_db_for_validator: Path):
    mock_client = MagicMock()
    coll = MagicMock()
    coll.name = "normativa"
    mock_client.get_collections.return_value.collections = [coll]

    # Solo c_1 está en Qdrant, falta c_2
    points = [
        _mock_point("p1", "c_1", text="Texto legal artículo 1"),
    ]
    mock_client.scroll.return_value = (points, None)

    exit_code, metrics = validate_correspondence(
        collection_name="normativa",
        db_path=test_db_for_validator,
        client=mock_client,
    )

    assert exit_code == 1
    assert metrics["missing_in_qdrant"] == 1


def test_validator_fails_on_text_mismatch(test_db_for_validator: Path):
    mock_client = MagicMock()
    coll = MagicMock()
    coll.name = "normativa"
    mock_client.get_collections.return_value.collections = [coll]

    # El texto de c_1 está alterado en Qdrant
    points = [
        _mock_point("p1", "c_1", text="TEXTO ALTERADO QUE NO COINCIDE"),
        _mock_point("p2", "c_2", text="Texto legal artículo 2"),
    ]
    mock_client.scroll.return_value = (points, None)

    exit_code, metrics = validate_correspondence(
        collection_name="normativa",
        db_path=test_db_for_validator,
        client=mock_client,
    )

    assert exit_code == 1
    assert metrics["text_mismatches"] == 1
    assert metrics["total_discrepancies"] >= 1


def test_validator_fails_when_family_or_cat_is_missing(test_db_for_validator: Path):
    mock_client = MagicMock()
    coll = MagicMock()
    coll.name = "normativa"
    mock_client.get_collections.return_value.collections = [coll]

    # Payload sin family_id ni categoria_id
    p1 = _mock_point("p1", "c_1", family_id=None, categoria_id=None, text="Texto legal artículo 1")
    p1.payload.pop("family_id")
    p1.payload.pop("categoria_id")
    points = [p1, _mock_point("p2", "c_2", text="Texto legal artículo 2")]
    mock_client.scroll.return_value = (points, None)

    exit_code, metrics = validate_correspondence(
        collection_name="normativa",
        db_path=test_db_for_validator,
        client=mock_client,
    )

    assert exit_code == 1
    assert metrics["missing_family_id"] == 1
    assert metrics["missing_categoria_id"] == 1
