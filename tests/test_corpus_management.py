from __future__ import annotations

import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from normativa.api.main import app
from normativa.config import settings
from normativa.corpus import db
from normativa.corpus.chunker import build_chunks_from_parsed_document
from normativa.corpus.models import (
    DocumentMetadata,
    NormativeVersion,
    ProcessingStatus,
)
from normativa.corpus.service import CorpusService
from normativa.ingestion.models import (
    Articulo,
    Inciso,
    Paragrafo,
    ParsedDocument,
    ParseReport,
)
from normativa.retrieval.indexer import QdrantCorpusIndexer


def _make_dummy_pdf(path: Path, title: str, year: int) -> Path:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 750, f"UNIDADES TECNOLÓGICAS DE SANTANDER")
    c.setFont("Helvetica", 11)
    c.drawString(72, 720, f"ACUERDO No. 01-{year}")
    c.drawString(72, 690, f"Por el cual se expide el {title}")
    c.drawString(72, 650, "CAPÍTULO I - DISPOSICIONES GENERALES")
    c.drawString(72, 620, "ARTÍCULO 1. Objeto y campo de aplicación de la presente norma.")
    c.drawString(72, 590, "Parágrafo 1. Este reglamento rige para toda la comunidad académica.")
    c.drawString(72, 560, "a) Primer caso de aplicación específica.")
    c.drawString(72, 530, "b) Segundo caso de aplicación específica.")
    c.drawString(72, 500, "ARTÍCULO 2. De los requisitos mínimos para optar a trabajo de grado.")
    c.drawString(72, 450, "PUBLÍQUESE Y CÚMPLASE")
    c.showPage()
    c.save()
    return path


def _dummy_embed_fn(text: str) -> list[float]:
    # Retorna un vector determinista de dimensión 1024
    vec = [0.0] * 1024
    vec[0] = float(len(text) % 100) / 100.0
    return vec


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "test_normativa.db"
    db.init_db(db_file)
    return db_file


@pytest.fixture
def mock_indexer() -> QdrantCorpusIndexer:
    mock_client = MagicMock()
    mock_collections = MagicMock()
    mock_collections.collections = []
    mock_client.get_collections.return_value = mock_collections
    mock_client.upsert.return_value = None
    mock_client.delete.return_value = None
    count_res = MagicMock()
    count_res.count = 5
    mock_client.count.return_value = count_res

    indexer = QdrantCorpusIndexer(
        qdrant_url="http://mock:6333",
        collection_name="test_normativa",
        client=mock_client,
    )
    return indexer


@pytest.fixture
def service(temp_db: Path, mock_indexer: QdrantCorpusIndexer) -> CorpusService:
    return CorpusService(db_path=temp_db, indexer=mock_indexer)


# --- 1. Se puede registrar un reglamento de 2019 ---
def test_1_register_reglamento_2019(tmp_path: Path, service: CorpusService, temp_db: Path) -> None:
    pdf_path = _make_dummy_pdf(tmp_path / "reglamento_2019.pdf", "Reglamento de Trabajo de Grado", 2019)
    pdf_bytes = pdf_path.read_bytes()

    doc, ver = service.register_document(
        file_bytes=pdf_bytes,
        filename="reglamento_2019.pdf",
        version_id="uts_tg_2019",
        nombre="Reglamento Trabajo de Grado 2019",
        numero_acuerdo="01-021",
        anio=2019,
        fecha_expedicion="2019-07-18",
        estado_vigencia="Derogado",
    )

    assert doc.filename == "reglamento_2019.pdf"
    assert doc.file_size_bytes == len(pdf_bytes)
    assert ver.id == "uts_tg_2019"
    assert ver.anio == 2019
    assert ver.status == ProcessingStatus.RECIBIDO
    assert not ver.is_active

    stored_ver = db.get_version("uts_tg_2019", db_path=temp_db)
    assert stored_ver is not None
    assert stored_ver.nombre == "Reglamento Trabajo de Grado 2019"


# --- 2. Se puede registrar otra versión sin sobrescribir la anterior ---
def test_2_register_multiple_versions_no_overwrite(tmp_path: Path, service: CorpusService, temp_db: Path) -> None:
    pdf2019 = _make_dummy_pdf(tmp_path / "reg_2019.pdf", "Reglamento 2019", 2019).read_bytes()
    pdf2021 = _make_dummy_pdf(tmp_path / "reg_2021.pdf", "Reglamento 2021", 2021).read_bytes()

    service.register_document(pdf2019, "reg_2019.pdf", "ver_2019", "Reglamento 2019", anio=2019)
    service.register_document(pdf2021, "reg_2021.pdf", "ver_2021", "Reglamento 2021", anio=2021)

    versions = db.list_versions(db_path=temp_db)
    ids = [v.id for v in versions]
    assert "ver_2019" in ids
    assert "ver_2021" in ids
    assert len(versions) == 2


# --- 3. Dos documentos de años distintos conservan sus propios identificadores y metadatos ---
def test_3_distinct_metadata_preserved(tmp_path: Path, service: CorpusService, temp_db: Path) -> None:
    pdf2019 = _make_dummy_pdf(tmp_path / "doc_19.pdf", "Normativa 2019", 2019).read_bytes()
    pdf2027 = _make_dummy_pdf(tmp_path / "doc_27.pdf", "Normativa Futura 2027", 2027).read_bytes()

    _, v1 = service.register_document(
        pdf2019, "doc_19.pdf", "v19", "Versión 2019", numero_acuerdo="01-2019", anio=2019
    )
    _, v2 = service.register_document(
        pdf2027, "doc_27.pdf", "v27", "Versión 2027", numero_acuerdo="04-2027", anio=2027
    )

    read_v1 = db.get_version("v19", db_path=temp_db)
    read_v2 = db.get_version("v27", db_path=temp_db)

    assert read_v1 is not None and read_v2 is not None
    assert read_v1.id == "v19" and read_v1.anio == 2019 and read_v1.numero_acuerdo == "01-2019"
    assert read_v2.id == "v27" and read_v2.anio == 2027 and read_v2.numero_acuerdo == "04-2027"
    assert read_v1.document_id != read_v2.document_id


# --- 4. Los chunks preservan la identificación de documento y versión ---
def test_4_chunks_preserve_document_and_version() -> None:
    parsed = ParsedDocument(
        source_file="synthetic.pdf",
        num_pages=3,
        preambulo="Preámbulo normativo institucional",
        articulos=[
            Articulo(
                kind="reglamento",
                numero=1,
                ordinal=None,
                capitulo_numero=1,
                capitulo_romano="I",
                capitulo_titulo="DISPOSICIONES",
                texto="Texto del artículo 1",
                incisos=[],
                paragrafos=[
                    Paragrafo(
                        numero="1",
                        texto="Texto del parágrafo 1",
                        incisos=[Inciso(marker="a", texto="Detalle inciso")],
                    )
                ],
                page_start=1,
                page_end=2,
                ocr_confidence_mean=95.0,
            )
        ],
        cierre="PUBLÍQUESE Y CÚMPLASE",
        report=ParseReport(),
    )

    chunks = build_chunks_from_parsed_document(
        parsed=parsed,
        version_id="ver_2025_prueba",
        document_id="doc_abc123",
        document_name="reglamento_2025.pdf",
    )

    assert len(chunks) >= 2
    for chunk in chunks:
        assert chunk.version_id == "ver_2025_prueba"
        assert chunk.document_id == "doc_abc123"
        assert chunk.document_name == "reglamento_2025.pdf"
        assert chunk.page_start > 0
        assert chunk.location_hint

    art_chunk = next(c for c in chunks if c.articulo_numero == 1 and c.paragrafo_numero is None)
    assert "Artículo 1" in art_chunk.location_hint
    assert art_chunk.capitulo_numero == 1

    par_chunk = next(c for c in chunks if c.articulo_numero == 1 and c.paragrafo_numero == "1")
    assert "Parágrafo 1" in par_chunk.location_hint
    assert "a) Detalle inciso" in par_chunk.texto


# --- 5. Los documentos escaneados utilizan OCR cuando corresponde ---
def test_5_scanned_documents_trigger_ocr(tmp_path: Path) -> None:
    from normativa.ingestion.extractor import extract_pages, should_use_text_layer

    # Verificar que el umbral y switch a OCR funcionan
    assert not should_use_text_layer("", min_chars=50, force_ocr=False)
    assert not should_use_text_layer("Texto muy corto", min_chars=50, force_ocr=False)
    assert not should_use_text_layer("Texto largo pero forzamos OCR...", min_chars=10, force_ocr=True)
    assert should_use_text_layer("Texto suficientemente extenso para capa nativa...", min_chars=20, force_ocr=False)


# --- 6. Los errores de OCR y procesamiento quedan registrados ---
def test_6_ocr_and_processing_errors_recorded(tmp_path: Path, service: CorpusService, temp_db: Path) -> None:
    # Subir un PDF inválido o dañado
    bad_pdf_path = tmp_path / "corrupt.pdf"
    bad_pdf_path.write_bytes(b"%PDF-1.4 corrupt content not a valid pdf header body...")

    service.register_document(
        file_bytes=bad_pdf_path.read_bytes(),
        filename="corrupt.pdf",
        version_id="ver_corrupt",
        nombre="Documento Dañado",
    )

    with pytest.raises(Exception):
        service.process_and_index_version("ver_corrupt")

    failed_ver = db.get_version("ver_corrupt", db_path=temp_db)
    assert failed_ver is not None
    assert failed_ver.status == ProcessingStatus.ERROR
    assert failed_ver.status_message is not None
    assert "Fallo" in failed_ver.status_message or "Error" in failed_ver.status_message


# --- 7. No se puede activar una versión sin indexación completa ---
def test_7_cannot_activate_incomplete_version(tmp_path: Path, service: CorpusService, temp_db: Path) -> None:
    pdf_bytes = _make_dummy_pdf(tmp_path / "test.pdf", "Reglamento", 2020).read_bytes()
    service.register_document(pdf_bytes, "test.pdf", "ver_incompleta", "Reglamento 2020")

    # Está en estado RECIBIDO, no PROCESADO
    ver = db.get_version("ver_incompleta", db_path=temp_db)
    assert ver is not None and ver.status == ProcessingStatus.RECIBIDO

    with pytest.raises(ValueError, match="Debe estar PROCESADO"):
        service.activate_version("ver_incompleta")

    ver_after = db.get_version("ver_incompleta", db_path=temp_db)
    assert ver_after is not None and not ver_after.is_active


def _create_test_version(
    version_id: str,
    nombre: str,
    anio: int,
    status: ProcessingStatus = ProcessingStatus.PROCESADO,
    is_active: bool = False,
    estado_revision: str = "APROBADO",
    db_path: Path | None = None,
) -> NormativeVersion:
    doc_id = f"doc_{version_id}"
    doc = DocumentMetadata(
        id=doc_id,
        filename=f"{version_id}.pdf",
        file_path=f"/fake/{version_id}.pdf",
        file_hash="dummy_hash",
        file_size_bytes=1000,
        uploaded_at="2026-01-01T00:00:00Z",
    )
    db.save_document(doc, db_path=db_path)
    ver = NormativeVersion(
        id=version_id,
        document_id=doc_id,
        nombre=nombre,
        numero_acuerdo=None,
        anio=anio,
        fecha_expedicion=None,
        estado_vigencia=None,
        status=status,
        status_message="OK",
        is_active=is_active,
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
        estado_revision=estado_revision,
    )
    db.save_version(ver, db_path=db_path)
    return ver


# --- 8. Activar una versión desactiva la selección de la anterior ---
def test_8_activating_version_deactivates_previous(temp_db: Path) -> None:
    _create_test_version("v_antigua", "Antigua", 2015, db_path=temp_db)
    _create_test_version("v_nueva", "Nueva", 2024, db_path=temp_db)

    # Activar v1
    db.activate_version("v_antigua", db_path=temp_db)
    assert db.get_version("v_antigua", db_path=temp_db).is_active is True
    assert db.get_version("v_nueva", db_path=temp_db).is_active is False

    # Activar v2
    db.activate_version("v_nueva", db_path=temp_db)
    assert db.get_version("v_antigua", db_path=temp_db).is_active is False
    assert db.get_version("v_nueva", db_path=temp_db).is_active is True


# --- 9. No pueden quedar dos versiones activas simultáneamente ---
def test_9_only_one_version_can_be_active_globally(temp_db: Path) -> None:
    for i in range(3):
        _create_test_version(f"v_{i}", f"Version {i}", 2020 + i, db_path=temp_db)

    db.activate_version("v_0", db_path=temp_db)
    db.activate_version("v_1", db_path=temp_db)
    db.activate_version("v_2", db_path=temp_db)

    all_vers = db.list_versions(db_path=temp_db)
    active_vers = [v for v in all_vers if v.is_active]
    assert len(active_vers) == 1
    assert active_vers[0].id == "v_2"


# --- 10. Se puede volver a activar una versión histórica ---
def test_10_reactivate_historical_version(temp_db: Path) -> None:
    _create_test_version("v_2019", "Reglamento 2019", 2019, db_path=temp_db)
    _create_test_version("v_2023", "Reglamento 2023", 2023, is_active=True, db_path=temp_db)

    # Reactivar versión de 2019
    db.activate_version("v_2019", db_path=temp_db)
    assert db.get_version("v_2019", db_path=temp_db).is_active is True
    assert db.get_version("v_2023", db_path=temp_db).is_active is False
    assert db.get_active_version(db_path=temp_db).id == "v_2019"


# --- 11. Los fallos de indexación no producen una versión falsamente disponible ---
def test_11_indexing_failure_cleans_up_and_marks_error(
    tmp_path: Path, service: CorpusService, temp_db: Path, mock_indexer: QdrantCorpusIndexer
) -> None:
    pdf_bytes = _make_dummy_pdf(tmp_path / "valid.pdf", "Reglamento", 2021).read_bytes()
    service.register_document(pdf_bytes, "valid.pdf", "ver_fail_idx", "Reglamento 2021")

    # Forzar error simulado en indexer
    mock_indexer._client.upsert.side_effect = RuntimeError("Error simulado de conexión a Qdrant")

    with pytest.raises(Exception):
        service.process_and_index_version("ver_fail_idx", embed_fn=_dummy_embed_fn)

    ver = db.get_version("ver_fail_idx", db_path=temp_db)
    assert ver is not None
    assert ver.status == ProcessingStatus.ERROR
    assert not ver.is_active

    # Intentar activarla debe fallar
    with pytest.raises(ValueError):
        service.activate_version("ver_fail_idx")


# --- 12. Errores de entrada o PDF inválido generan respuestas HTTP controladas ---
def test_12_api_input_validation_and_security(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    test_db = tmp_path / "api_test.db"
    db.init_db(test_db)
    monkeypatch.setattr(settings, "SQLITE_PATH", str(test_db))
    monkeypatch.setattr(settings, "ADMIN_API_KEY", "test-secret-key-123")

    client = TestClient(app)

    # 12.1 Sin autenticación en endpoint admin -> 401
    res_no_auth = client.post("/api/admin/documents")
    assert res_no_auth.status_code == 401
    assert "Credencial administrativa" in res_no_auth.json()["detail"]

    # 12.2 Con credencial errónea -> 401
    res_bad_auth = client.post(
        "/api/admin/documents",
        headers={"X-Admin-Key": "wrong-key"},
    )
    assert res_bad_auth.status_code == 401

    # 12.3 Con credencial correcta pero sin archivo PDF -> 400
    res_no_pdf = client.post(
        "/api/admin/documents",
        headers={"X-Admin-Key": "test-secret-key-123"},
        data={"version_id": "v1", "nombre": "Test"},
        files={"file": ("test.txt", b"Texto plano", "text/plain")},
    )
    assert res_no_pdf.status_code == 400
    assert "documento PDF" in res_no_pdf.json()["detail"]

    # 12.4 Archivo vacío (0 bytes) -> 400
    res_empty_pdf = client.post(
        "/api/admin/documents",
        headers={"X-Admin-Key": "test-secret-key-123"},
        data={"version_id": "v1", "nombre": "Test"},
        files={"file": ("vacio.pdf", b"", "application/pdf")},
    )
    assert res_empty_pdf.status_code == 400
    assert "vacío" in res_empty_pdf.json()["detail"]

    # 12.5 Carga exitosa de un PDF válido
    valid_pdf = _make_dummy_pdf(tmp_path / "valid.pdf", "Reglamento API", 2022).read_bytes()
    res_ok = client.post(
        "/api/admin/documents",
        headers={"X-Admin-Key": "test-secret-key-123"},
        data={
            "version_id": "v_api_2022",
            "nombre": "Reglamento API 2022",
            "anio": "2022",
            "auto_process": "false",
        },
        files={"file": ("valid.pdf", valid_pdf, "application/pdf")},
    )
    assert res_ok.status_code == 201
    body = res_ok.json()
    assert body["version"]["id"] == "v_api_2022"
    assert body["version"]["status"] == "RECIBIDO"

    # 12.6 Duplicar version_id -> 409 Conflict
    res_dup = client.post(
        "/api/admin/documents",
        headers={"X-Admin-Key": "test-secret-key-123"},
        data={"version_id": "v_api_2022", "nombre": "Duplicado", "auto_process": "false"},
        files={"file": ("valid.pdf", valid_pdf, "application/pdf")},
    )
    assert res_dup.status_code == 409

    # 12.7 Activar versión no existente -> 400 o 404
    res_act_missing = client.post(
        "/api/admin/versions/non_existent/activate",
        headers={"X-Admin-Key": "test-secret-key-123"},
    )
    assert res_act_missing.status_code == 400

    # 12.8 Endpoint público de versión activa cuando no hay ninguna
    res_public_active = client.get("/api/versions/active")
    assert res_public_active.status_code == 200
    assert res_public_active.json()["has_active_version"] is False
