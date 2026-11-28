"""Pruebas automatizadas para scripts/migrate_qdrant_payloads.py."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from normativa.corpus import db
from normativa.corpus.models import DocumentCategory, DocumentFamily, DocumentMetadata, NormativeVersion, ProcessingStatus
from scripts.migrate_qdrant_payloads import load_sqlite_chunks, run_migration


@pytest.fixture
def test_db_environment(tmp_path: Path):
    db_file = tmp_path / "test_normativa.db"
    db.init_db(db_file)

    # 1. Categoría y Familia
    cat = DocumentCategory(id="cat_reglamentos", nombre="Reglamentos", descripcion="Test", estado="ACTIVO")
    fam = DocumentFamily(id="fam_reglamento_tg", categoria_id="cat_reglamentos", codigo="RTG", nombre="Reglamento TG", descripcion="Test", estado="ACTIVO")
    db.create_category(cat, db_file)
    db.create_family(fam, db_file)

    # 2. Documento y Versión
    doc = DocumentMetadata(
        id="doc_001",
        filename="reglamento.pdf",
        file_path="/tmp/reg.pdf",
        file_hash="hash001",
        file_size_bytes=1000,
        uploaded_at="2026-11-27T00:00:00",
    )
    db.save_document(doc, db_file)

    ver = NormativeVersion(
        id="ver_001",
        document_id="doc_001",
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

    # 3. Chunks en SQLite
    conn = sqlite3.connect(str(db_file))
    conn.execute(
        """
        INSERT INTO chunks (
            id, version_id, document_id, document_name, capitulo_numero,
            articulo_numero, articulo_tipo, page_start, page_end, texto,
            location_hint, created_at, family_id, categoria_id
        ) VALUES
        ('chunk_1', 'ver_001', 'doc_001', 'reglamento.pdf', 1, 1, 'ARTICULO', 1, 1, 'Texto art 1', 'Art 1', '2026-11-27', 'fam_reglamento_tg', 'cat_reglamentos'),
        ('chunk_2', 'ver_001', 'doc_001', 'reglamento.pdf', 1, 2, 'ARTICULO', 1, 1, 'Texto art 2', 'Art 2', '2026-11-27', 'fam_reglamento_tg', 'cat_reglamentos')
        """
    )
    conn.commit()
    conn.close()

    return db_file


def _mock_point(point_id: str, chunk_id: str, version_id: str = "ver_001", doc_id: str = "doc_001", family_id: str | None = None, categoria_id: str | None = None):
    p = MagicMock()
    p.id = point_id
    p.payload = {
        "chunk_id": chunk_id,
        "version_id": version_id,
        "document_id": doc_id,
        "text": f"Texto {chunk_id}",
    }
    if family_id:
        p.payload["family_id"] = family_id
    if categoria_id:
        p.payload["categoria_id"] = categoria_id
    return p


def test_dry_run_identifies_pending_updates(test_db_environment: Path):
    mock_client = MagicMock()
    coll = MagicMock()
    coll.name = "test_collection"
    mock_client.get_collections.return_value.collections = [coll]

    # Dos puntos en Qdrant sin family_id ni categoria_id
    points = [
        _mock_point("p1", "chunk_1"),
        _mock_point("p2", "chunk_2"),
    ]
    mock_client.scroll.return_value = (points, None)

    exit_code, stats = run_migration(
        collection_name="test_collection",
        db_path=test_db_environment,
        dry_run=True,
        client=mock_client,
    )

    assert exit_code == 0
    assert stats["inspected"] == 2
    assert stats["pending"] == 2
    assert stats["already_ok"] == 0
    assert stats["updated"] == 0
    assert stats["inconsistent"] == 0
    # En dry-run NO debe llamar a set_payload
    mock_client.set_payload.assert_not_called()


def test_migration_writes_payloads(test_db_environment: Path):
    mock_client = MagicMock()
    coll = MagicMock()
    coll.name = "test_collection"
    mock_client.get_collections.return_value.collections = [coll]

    points = [
        _mock_point("p1", "chunk_1"),
        _mock_point("p2", "chunk_2"),
    ]
    mock_client.scroll.return_value = (points, None)

    exit_code, stats = run_migration(
        collection_name="test_collection",
        db_path=test_db_environment,
        dry_run=False,
        client=mock_client,
    )

    assert exit_code == 0
    assert stats["updated"] == 2
    assert stats["failed"] == 0
    assert mock_client.set_payload.call_count == 2

    # Verificar argumentos del set_payload
    first_call_kwargs = mock_client.set_payload.call_args_list[0][1]
    assert first_call_kwargs["collection_name"] == "test_collection"
    assert first_call_kwargs["wait"] is True
    assert first_call_kwargs["payload"] == {
        "family_id": "fam_reglamento_tg",
        "categoria_id": "cat_reglamentos",
    }


def test_migration_idempotence(test_db_environment: Path):
    mock_client = MagicMock()
    coll = MagicMock()
    coll.name = "test_collection"
    mock_client.get_collections.return_value.collections = [coll]

    # Puntos que ya tienen los campos correctos
    points = [
        _mock_point("p1", "chunk_1", family_id="fam_reglamento_tg", categoria_id="cat_reglamentos"),
        _mock_point("p2", "chunk_2", family_id="fam_reglamento_tg", categoria_id="cat_reglamentos"),
    ]
    mock_client.scroll.return_value = (points, None)

    exit_code, stats = run_migration(
        collection_name="test_collection",
        db_path=test_db_environment,
        dry_run=False,
        client=mock_client,
    )

    assert exit_code == 0
    assert stats["inspected"] == 2
    assert stats["pending"] == 0
    assert stats["already_ok"] == 2
    assert stats["updated"] == 0
    mock_client.set_payload.assert_not_called()


def test_prevalidation_aborts_on_inconsistent_orphan_point(test_db_environment: Path):
    mock_client = MagicMock()
    coll = MagicMock()
    coll.name = "test_collection"
    mock_client.get_collections.return_value.collections = [coll]

    # Punto p_orphan con chunk_id inexistente en SQLite
    points = [
        _mock_point("p1", "chunk_1"),
        _mock_point("p_orphan", "chunk_fantasma"),
    ]
    mock_client.scroll.return_value = (points, None)

    exit_code, stats = run_migration(
        collection_name="test_collection",
        db_path=test_db_environment,
        dry_run=False,
        client=mock_client,
    )

    # Debe fallar y NO escribir absolutamente nada
    assert exit_code == 1
    assert stats["inconsistent"] > 0
    assert stats["updated"] == 0
    mock_client.set_payload.assert_not_called()


def test_prevalidation_aborts_on_version_mismatch(test_db_environment: Path):
    mock_client = MagicMock()
    coll = MagicMock()
    coll.name = "test_collection"
    mock_client.get_collections.return_value.collections = [coll]

    # Punto p1 con version_id distinta a la de SQLite ('ver_distinta' != 'ver_001')
    points = [
        _mock_point("p1", "chunk_1", version_id="ver_distinta"),
        _mock_point("p2", "chunk_2"),
    ]
    mock_client.scroll.return_value = (points, None)

    exit_code, stats = run_migration(
        collection_name="test_collection",
        db_path=test_db_environment,
        dry_run=False,
        client=mock_client,
    )

    assert exit_code == 1
    assert stats["inconsistent"] > 0
    assert stats["updated"] == 0
    mock_client.set_payload.assert_not_called()


def test_migration_handles_write_failure(test_db_environment: Path):
    mock_client = MagicMock()
    coll = MagicMock()
    coll.name = "test_collection"
    mock_client.get_collections.return_value.collections = [coll]

    points = [
        _mock_point("p1", "chunk_1"),
        _mock_point("p2", "chunk_2"),
    ]
    mock_client.scroll.return_value = (points, None)
    mock_client.set_payload.side_effect = RuntimeError("Conexión perdida")

    exit_code, stats = run_migration(
        collection_name="test_collection",
        db_path=test_db_environment,
        dry_run=False,
        client=mock_client,
    )

    assert exit_code == 1
    assert stats["failed"] == 2
    assert stats["updated"] == 0
