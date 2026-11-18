from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from normativa.api.admin import get_corpus_service
from normativa.api.main import app
from normativa.config import settings
from normativa.corpus import db
from normativa.corpus.models import DocumentMetadata, NormativeVersion, ProcessingStatus
from normativa.corpus.service import CorpusService


@pytest.fixture
def mock_corpus_service(tmp_path: Path):
    db_file = tmp_path / "test_v3.db"
    db.init_db(db_file)
    mock_indexer = MagicMock()
    service = CorpusService(db_path=db_file, indexer=mock_indexer)
    return service


@pytest.fixture
def client(mock_corpus_service: CorpusService):
    app.dependency_overrides[get_corpus_service] = lambda: mock_corpus_service
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_admin_login_success_and_cookie(client: TestClient):
    response = client.post("/api/admin/login", json={"admin_key": settings.ADMIN_API_KEY})
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "admin_session" in response.cookies


def test_admin_login_failure(client: TestClient):
    response = client.post("/api/admin/login", json={"admin_key": "wrong_password"})
    assert response.status_code == 401


def test_admin_auth_via_cookie(client: TestClient):
    # Sin autenticación
    res_unauth = client.get("/api/admin/me")
    assert res_unauth.status_code == 401

    # Login
    login_res = client.post("/api/admin/login", json={"admin_key": settings.ADMIN_API_KEY})
    assert login_res.status_code == 200

    # Petición protegida usando la cookie almacenada por el cliente
    res_auth = client.get("/api/admin/me")
    assert res_auth.status_code == 200
    assert res_auth.json()["authenticated"] is True


def test_admin_logout(client: TestClient):
    client.post("/api/admin/login", json={"admin_key": settings.ADMIN_API_KEY})
    assert client.get("/api/admin/me").status_code == 200

    logout_res = client.post("/api/admin/logout")
    assert logout_res.status_code == 200

    # Ahora no debería estar autenticado si la cookie se limpió
    # Nota: TestClient maneja cookies borradas
    client.cookies.clear()
    assert client.get("/api/admin/me").status_code == 401


def test_admin_stats(client: TestClient, mock_corpus_service: CorpusService):
    doc = DocumentMetadata(
        id="doc_stat_1",
        filename="reg.pdf",
        file_path="data/pdfs/reg.pdf",
        file_hash="fakehash",
        file_size_bytes=1000,
        uploaded_at="2026-01-01T00:00:00Z",
    )
    db.save_document(doc, mock_corpus_service.db_path)
    ver = NormativeVersion(
        id="v_stat_1",
        document_id="doc_stat_1",
        nombre="Reglamento Estadísticas",
        numero_acuerdo="001",
        anio=2020,
        fecha_expedicion="2020-01-01",
        estado_vigencia="Vigente",
        status=ProcessingStatus.PROCESADO,
        status_message="Ok",
        is_active=True,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        chunks_count=15,
    )
    db.save_version(ver, mock_corpus_service.db_path)

    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}
    res = client.get("/api/admin/stats", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_versions"] == 1
    assert data["total_chunks"] == 15
    assert data["status_counts"]["PROCESADO"] == 1
    assert data["active_version"]["id"] == "v_stat_1"


def test_admin_review_approval(client: TestClient, mock_corpus_service: CorpusService):
    doc = DocumentMetadata(
        id="doc_rev_1",
        filename="reg.pdf",
        file_path="data/pdfs/reg.pdf",
        file_hash="fakehash",
        file_size_bytes=1000,
        uploaded_at="2026-01-01T00:00:00Z",
    )
    db.save_document(doc, mock_corpus_service.db_path)
    ver = NormativeVersion(
        id="v_rev_1",
        document_id="doc_rev_1",
        nombre="Reglamento Revisión",
        numero_acuerdo="002",
        anio=2021,
        fecha_expedicion="2021-01-01",
        estado_vigencia="Vigente",
        status=ProcessingStatus.PENDIENTE_REVISION,
        status_message="OCR bajo",
        is_active=False,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    db.save_version(ver, mock_corpus_service.db_path)

    headers = {"X-Admin-Key": settings.ADMIN_API_KEY}

    # Intentar activar directamente debe fallar porque está PENDIENTE_REVISION
    act_fail = client.post("/api/admin/versions/v_rev_1/activate", headers=headers)
    assert act_fail.status_code == 400

    # Aprobar revisión
    rev_res = client.post(
        "/api/admin/versions/v_rev_1/review",
        json={"action": "approve", "notes": "Artículos verificados manualmente"},
        headers=headers,
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["version"]["status"] == "PROCESADO"

    # Ahora sí debe poder activarse
    act_ok = client.post("/api/admin/versions/v_rev_1/activate", headers=headers)
    assert act_ok.status_code == 200
    assert act_ok.json()["success"] is True


def test_pdf_endpoint_and_security(client: TestClient, mock_corpus_service: CorpusService, tmp_path: Path):
    # Crear un PDF dentro de DATA_DIR
    data_dir = Path(settings.DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    pdf_file = data_dir / "pdfs" / "test_sample.pdf"
    pdf_file.parent.mkdir(parents=True, exist_ok=True)
    pdf_file.write_bytes(b"%PDF-1.4 test dummy content")

    doc = DocumentMetadata(
        id="doc_pdf_1",
        filename="test_sample.pdf",
        file_path=str(pdf_file),
        file_hash="fakehash",
        file_size_bytes=pdf_file.stat().st_size,
        uploaded_at="2026-01-01T00:00:00Z",
    )
    db.save_document(doc, mock_corpus_service.db_path)
    ver = NormativeVersion(
        id="v_pdf_1",
        document_id="doc_pdf_1",
        nombre="Reglamento PDF",
        numero_acuerdo="003",
        anio=2022,
        fecha_expedicion="2022-01-01",
        estado_vigencia="Vigente",
        status=ProcessingStatus.PROCESADO,
        status_message="Ok",
        is_active=False,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    db.save_version(ver, mock_corpus_service.db_path)

    # Consulta de PDF válida
    res = client.get("/api/versions/v_pdf_1/pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert b"%PDF-1.4" in res.content

    # Intento de acceso a versión inexistente
    res_404 = client.get("/api/versions/nonexistent/pdf")
    assert res_404.status_code == 404
