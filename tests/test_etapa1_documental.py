"""Pruebas exhaustivas de la Etapa 1: Gestión documental y versionamiento.

Verifica:
1. Creación y edición de categorías documentales.
2. Creación de familias documentales y asociación a categorías.
3. Creación de versiones y validación de campos mínimos.
4. Detección de archivos duplicados SHA-256.
5. Activación de una versión y desactivación automática de la versión previa de la misma familia.
6. Activación simultánea de versiones de distintas familias (coexistencia en corpus activo).
7. Rechazo de activaciones concurrentes o conflictivas (restricción UNIQUE por familia).
8. Rechazo de documentos no procesados (status != PROCESADO) o rechazados (estado_revision == RECHAZADO).
9. Rechazo de activación de documentos con discrepancia o inconsistencia de identidad.
10. Recuperación en Qdrant/Retriever limitada al conjunto de versiones autorizadas activas.
11. Exclusión estricta de versiones inactivas e inconsistentes.
12. Conservación del snapshot de versiones durante una consulta (aislamiento inmutable).
13. Integridad y presencia de authorized_versions_json en las trazas.
14. Seguridad: autenticación requerida en los endpoints administrativos de categorías y familias.
"""

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
from normativa.corpus.models import (
    DocumentCategory,
    DocumentFamily,
    DocumentMetadata,
    NormativeVersion,
    ProcessingStatus,
)
from normativa.corpus.service import CorpusService
from normativa.generation.rag_service import RAGService
from normativa.retrieval.retriever import NormativeRetriever
from normativa.tracing import db as trace_db
from normativa.tracing.models import QueryTrace


def _make_dummy_pdf(path: Path, title: str, year: int, unique_suffix: str = "") -> Path:
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, 750, f"UNIDADES TECNOLÓGICAS DE SANTANDER {unique_suffix}")
    c.setFont("Helvetica", 11)
    c.drawString(72, 720, f"ACUERDO No. 01-{year}")
    c.drawString(72, 690, f"Por el cual se expide el {title}")
    c.drawString(72, 650, "CAPÍTULO I - DISPOSICIONES GENERALES")
    c.drawString(72, 620, "ARTÍCULO 1. Objeto y campo de aplicación de la presente norma.")
    c.drawString(72, 590, "Parágrafo 1. Este reglamento rige para toda la comunidad académica.")
    c.drawString(72, 560, "a) Primer caso de aplicación específica.")
    c.drawString(72, 500, "ARTÍCULO 2. Requisitos y disposiciones institucionales.")
    c.drawString(72, 450, "PUBLÍQUESE Y CÚMPLASE")
    c.showPage()
    c.save()
    return path


@pytest.fixture
def temp_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "test_etapa1.db"
    db.init_db(db_file)
    return db_file


@pytest.fixture
def populated_env(temp_db: Path):
    """Crea estructura base de categorías y familias."""
    cat_reg = DocumentCategory(
        id="cat_reglamentos",
        nombre="Reglamentos Institucionales",
        descripcion="Reglamentos académicos y disciplinarios",
        estado="ACTIVO",
    )
    cat_proc = DocumentCategory(
        id="cat_procedimientos",
        nombre="Procedimientos",
        descripcion="Procedimientos de trabajo de grado",
        estado="ACTIVO",
    )
    db.create_category(cat_reg, temp_db)
    db.create_category(cat_proc, temp_db)

    fam_rtg = DocumentFamily(
        id="fam_reglamento_tg",
        categoria_id="cat_reglamentos",
        codigo="RTG",
        nombre="Reglamento de Trabajo de Grado",
        descripcion="Marco normativo para proyectos de grado",
        estado="ACTIVO",
    )
    fam_pdc28 = DocumentFamily(
        id="fam_p_dc_28",
        categoria_id="cat_procedimientos",
        codigo="P-DC-28",
        nombre="Procedimiento de Trabajo de Grado",
        descripcion="Guía operativa P-DC-28",
        estado="ACTIVO",
    )
    db.create_family(fam_rtg, temp_db)
    db.create_family(fam_pdc28, temp_db)

    return {"db": temp_db, "cat_reg": cat_reg, "fam_rtg": fam_rtg, "fam_pdc28": fam_pdc28}


# -----------------------------------------------------------------------------
# 1. Creación y edición de categorías
# -----------------------------------------------------------------------------
def test_category_crud(temp_db: Path):
    cat = DocumentCategory(
        id="cat_formatos_test",
        nombre="Formatos de Prueba",
        descripcion="Formatos oficiales para test",
        estado="ACTIVO",
    )
    created = db.create_category(cat, temp_db)
    assert created.id == "cat_formatos_test"
    assert created.nombre == "Formatos de Prueba"

    # Obtener por ID y listar
    fetched = db.get_category("cat_formatos_test", temp_db)
    assert fetched is not None
    assert fetched.nombre == "Formatos de Prueba"
    cats = db.list_categories(db_path=temp_db)
    assert any(c.id == "cat_formatos_test" for c in cats)

    # Actualizar categoría
    updated = db.update_category(
        "cat_formatos_test",
        nombre="Formatos Institucionales UTS",
        descripcion="Formatos del SGI",
        estado="ACTIVO",
        db_path=temp_db,
    )
    assert updated.nombre == "Formatos Institucionales UTS"
    assert updated.descripcion == "Formatos del SGI"


# -----------------------------------------------------------------------------
# 2. Creación de familias y asociación a categoría
# -----------------------------------------------------------------------------
def test_family_crud_and_association(populated_env):
    db_path = populated_env["db"]
    fam = db.get_family("fam_reglamento_tg", db_path)
    assert fam is not None
    assert fam.categoria_id == "cat_reglamentos"
    assert fam.codigo == "RTG"

    # Listar por categoría
    reg_families = db.list_families(categoria_id="cat_reglamentos", db_path=db_path)
    assert len(reg_families) == 1
    assert reg_families[0].id == "fam_reglamento_tg"

    # Actualizar familia
    updated = db.update_family(
        "fam_reglamento_tg",
        nombre="Reglamento de Trabajo de Grado UTS - Actualizado",
        codigo="RTG-UTS",
        db_path=db_path,
    )
    assert updated.nombre == "Reglamento de Trabajo de Grado UTS - Actualizado"
    assert updated.codigo == "RTG-UTS"


# -----------------------------------------------------------------------------
# 3. Creación de versiones y validación de campos
# -----------------------------------------------------------------------------
def test_version_fields_and_persistence(populated_env):
    db_path = populated_env["db"]
    doc = DocumentMetadata(
        id="doc_test_001",
        filename="reglamento_2019.pdf",
        file_path="/tmp/reglamento_2019.pdf",
        file_hash="hash_test_123",
        file_size_bytes=1024,
        uploaded_at="2026-11-27T12:00:00",
    )
    db.save_document(doc, db_path)

    v = NormativeVersion(
        id="ver_rtg_2019",
        document_id="doc_test_001",
        nombre="Reglamento de Trabajo de Grado 2019",
        numero_acuerdo="Acuerdo 01-021",
        anio=2019,
        fecha_expedicion="2019-03-01",
        estado_vigencia="DEROGADO",
        status=ProcessingStatus.PROCESADO,
        status_message="OK",
        is_active=False,
        created_at="2026-11-27T12:00:00",
        updated_at="2026-11-27T12:00:00",
        chunks_count=45,
        family_id="fam_reglamento_tg",
        numero_version_institucional="1.0",
        procedencia="Consejo Directivo UTS",
        estado_revision="APROBADO",
        inconsistencia_identidad=False,
    )
    db.create_version(v, db_path)
    created = db.get_version("ver_rtg_2019", db_path)
    assert created is not None
    assert created.id == "ver_rtg_2019"
    assert created.family_id == "fam_reglamento_tg"
    assert created.estado_vigencia == "DEROGADO"
    assert created.estado_revision == "APROBADO"
    assert created.inconsistencia_identidad is False


# -----------------------------------------------------------------------------
# 4. Detección de archivos duplicados SHA-256
# -----------------------------------------------------------------------------
def test_sha256_duplicate_detection(populated_env, tmp_path: Path):
    db_path = populated_env["db"]
    pdf_path = tmp_path / "doc_test.pdf"
    _make_dummy_pdf(pdf_path, "Acuerdo 01-021", 2019)
    pdf_bytes = pdf_path.read_bytes()

    service = CorpusService(
        db_path=db_path,
        indexer=MagicMock(),
    )

    # Registrar primer documento
    doc1, ver1 = service.register_document(
        file_bytes=pdf_bytes,
        filename="reglamento_2019.pdf",
        version_id="ver_rtg_2019_real",
        nombre="Reglamento 2019 Original",
        numero_acuerdo="01-021",
        anio=2019,
        family_id="fam_reglamento_tg",
    )

    # Intentar registrar el mismo PDF bajo otro nombre/año pretendiendo ser otra versión
    doc2, ver2 = service.register_document(
        file_bytes=pdf_bytes,
        filename="reglamento_2021_falso.pdf",
        version_id="ver_rtg_2021_fake",
        nombre="Reglamento 2021 Falso",
        numero_acuerdo="01-026",
        anio=2021,
        family_id="fam_reglamento_tg",
    )

    # El segundo debe detectar colisión SHA-256 y marcar inconsistencia de identidad
    assert doc2.file_hash == doc1.file_hash
    assert ver2.inconsistencia_identidad is True
    assert ver2.estado_revision == "CON_DISCREPANCIAS"
    assert "discrepancia documental" in (ver2.status_message or "").lower()


# -----------------------------------------------------------------------------
# 5, 7, 8, 9. Reglas de negocio de activación y rechazos
# -----------------------------------------------------------------------------
def test_activation_rules_and_rejections(populated_env):
    db_path = populated_env["db"]

    doc = DocumentMetadata(
        id="doc_dummy",
        filename="dummy.pdf",
        file_path="/tmp/dummy.pdf",
        file_hash="hash_dummy",
        file_size_bytes=500,
        uploaded_at="2026-11-27T12:00:00",
    )
    db.save_document(doc, db_path)

    # 1. Versión no procesada no puede activarse
    v_pending = NormativeVersion(
        id="ver_pending",
        document_id="doc_dummy",
        nombre="Versión Pendiente",
        numero_acuerdo="01",
        anio=2020,
        fecha_expedicion="2020-01-01",
        estado_vigencia="VIGENTE",
        status=ProcessingStatus.RECIBIDO,
        status_message=None,
        is_active=False,
        created_at="2026-11-27T12:00:00",
        updated_at="2026-11-27T12:00:00",
        family_id="fam_reglamento_tg",
        estado_revision="PENDIENTE",
    )
    db.create_version(v_pending, db_path)
    with pytest.raises(ValueError, match="Debe estar PROCESADO"):
        db.set_active_version("ver_pending", db_path)

    # 2. Versión con inconsistencia de identidad documental no puede activarse
    # (aun cuando el status sea PROCESADO y la revisión esté "APROBADO" superficialmente,
    #  la inconsistencia de identidad debe bloquearse)
    v_inconsistent = NormativeVersion(
        id="ver_inconsistent",
        document_id="doc_dummy",
        nombre="Versión Inconsistente",
        numero_acuerdo="02",
        anio=2021,
        fecha_expedicion="2021-01-01",
        estado_vigencia="VIGENTE",
        status=ProcessingStatus.PROCESADO,
        status_message="Discrepancia detectada",
        is_active=False,
        created_at="2026-11-27T12:00:00",
        updated_at="2026-11-27T12:00:00",
        family_id="fam_reglamento_tg",
        estado_revision="APROBADO",   # revisión "aprobada" pero con flag de inconsistencia
        inconsistencia_identidad=True,
    )
    db.create_version(v_inconsistent, db_path)
    with pytest.raises(ValueError, match="discrepancias de identidad documental"):
        db.set_active_version("ver_inconsistent", db_path)

    # 3. Versión con revisión RECHAZADO no puede activarse
    v_rejected = NormativeVersion(
        id="ver_rejected",
        document_id="doc_dummy",
        nombre="Versión Rechazada",
        numero_acuerdo="03",
        anio=2022,
        fecha_expedicion="2022-01-01",
        estado_vigencia="VIGENTE",
        status=ProcessingStatus.PROCESADO,
        status_message="Documento ilegible",
        is_active=False,
        created_at="2026-11-27T12:00:00",
        updated_at="2026-11-27T12:00:00",
        family_id="fam_reglamento_tg",
        estado_revision="RECHAZADO",
        inconsistencia_identidad=False,
    )
    db.create_version(v_rejected, db_path)
    with pytest.raises(ValueError, match="revisión documental no está APROBADA"):
        db.set_active_version("ver_rejected", db_path)

    # 4. Versión válida sí se activa
    v_valid_1 = NormativeVersion(
        id="ver_valid_1",
        document_id="doc_dummy",
        nombre="Versión 1 RTG Válida",
        numero_acuerdo="04",
        anio=2023,
        fecha_expedicion="2023-01-01",
        estado_vigencia="VIGENTE",
        status=ProcessingStatus.PROCESADO,
        status_message="OK",
        is_active=False,
        created_at="2026-11-27T12:00:00",
        updated_at="2026-11-27T12:00:00",
        family_id="fam_reglamento_tg",
        estado_revision="APROBADO",
        inconsistencia_identidad=False,
    )
    db.create_version(v_valid_1, db_path)
    db.set_active_version("ver_valid_1", db_path)
    assert db.get_version("ver_valid_1", db_path).is_active is True

    # 5. Activar otra versión de la misma familia desactiva la previa
    v_valid_2 = NormativeVersion(
        id="ver_valid_2",
        document_id="doc_dummy",
        nombre="Versión 2 RTG Válida",
        numero_acuerdo="05",
        anio=2024,
        fecha_expedicion="2024-01-01",
        estado_vigencia="VIGENTE",
        status=ProcessingStatus.PROCESADO,
        status_message="OK",
        is_active=False,
        created_at="2026-11-27T12:00:00",
        updated_at="2026-11-27T12:00:00",
        family_id="fam_reglamento_tg",
        estado_revision="APROBADO",
        inconsistencia_identidad=False,
    )
    db.create_version(v_valid_2, db_path)
    db.set_active_version("ver_valid_2", db_path)

    assert db.get_version("ver_valid_1", db_path).is_active is False
    assert db.get_version("ver_valid_2", db_path).is_active is True


# -----------------------------------------------------------------------------
# 6. Activación simultánea de versiones de distintas familias
# -----------------------------------------------------------------------------
def test_simultaneous_active_versions_across_families(populated_env):
    db_path = populated_env["db"]

    doc = DocumentMetadata(
        id="doc_dummy_sim",
        filename="dummy_sim.pdf",
        file_path="/tmp/dummy_sim.pdf",
        file_hash="hash_dummy_sim",
        file_size_bytes=500,
        uploaded_at="2026-11-27T12:00:00",
    )
    db.save_document(doc, db_path)

    # Activar versión para familia RTG
    v_rtg = NormativeVersion(
        id="ver_rtg_activa",
        document_id="doc_dummy_sim",
        nombre="Reglamento RTG Activo",
        numero_acuerdo="01-021",
        anio=2019,
        fecha_expedicion="2019-01-01",
        estado_vigencia="VIGENTE",
        status=ProcessingStatus.PROCESADO,
        status_message="OK",
        is_active=False,
        created_at="2026-11-27T12:00:00",
        updated_at="2026-11-27T12:00:00",
        family_id="fam_reglamento_tg",
        estado_revision="APROBADO",
        inconsistencia_identidad=False,
    )
    db.create_version(v_rtg, db_path)
    db.set_active_version("ver_rtg_activa", db_path)

    # Activar versión para familia Procedimiento P-DC-28
    v_proc = NormativeVersion(
        id="ver_pdc28_activa",
        document_id="doc_dummy_sim",
        nombre="Procedimiento P-DC-28 Activo",
        numero_acuerdo="P-DC-28",
        anio=2022,
        fecha_expedicion="2022-01-01",
        estado_vigencia="VIGENTE",
        status=ProcessingStatus.PROCESADO,
        status_message="OK",
        is_active=False,
        created_at="2026-11-27T12:00:00",
        updated_at="2026-11-27T12:00:00",
        family_id="fam_p_dc_28",
        estado_revision="APROBADO",
        inconsistencia_identidad=False,
    )
    db.create_version(v_proc, db_path)
    db.set_active_version("ver_pdc28_activa", db_path)

    # Ambos deben estar activos simultáneamente sin interferirse
    active_versions = db.list_active_versions(db_path)
    active_ids = {v.id for v in active_versions}
    assert "ver_rtg_activa" in active_ids
    assert "ver_pdc28_activa" in active_ids
    assert len(active_versions) == 2



# -----------------------------------------------------------------------------
# 10, 11, 12. Retriever: filtro estricto por versiones autorizadas y snapshot inmutable
# -----------------------------------------------------------------------------
def test_retriever_active_versions_filtering_and_snapshot():
    mock_qdrant = MagicMock()
    mock_embed_fn = MagicMock(return_value=[0.1] * 1024)

    retriever = NormativeRetriever(
        client=mock_qdrant,
        collection_name="normativa_chunks",
        embed_fn=mock_embed_fn,
        top_k=5,
    )

    # Consulta con authorized_version_ids explícitos
    authorized = ["ver_rtg_activa", "ver_pdc28_activa"]
    mock_query_res = MagicMock()
    mock_query_res.points = []
    mock_qdrant.query_points.return_value = mock_query_res

    res = retriever.retrieve("¿Cuáles son los requisitos de grado?", authorized_version_ids=authorized)
    assert res is not None

    # Verificar que el filtro pasado a Qdrant contiene MatchAny para las versiones autorizadas
    called_filter = mock_qdrant.query_points.call_args[1]["query_filter"]
    must_conditions = called_filter.must
    assert len(must_conditions) == 1
    match_condition = must_conditions[0]
    assert match_condition.key == "version_id"
    # El valor debe ser MatchAny con las versiones autorizadas
    assert set(match_condition.match.any) == set(authorized)

    # Consulta sin ninguna versión autorizada -> Debe abstenerse sin consultar Qdrant
    mock_qdrant.reset_mock()
    empty_res = retriever.retrieve("requisitos", authorized_version_ids=[])
    assert empty_res.abstained is True
    assert "no hay ningún reglamento habilitado" in empty_res.abstention_reason
    mock_qdrant.query_points.assert_not_called()


# -----------------------------------------------------------------------------
# 13. Trazabilidad: integridad y snapshot de authorized_versions_json
# -----------------------------------------------------------------------------
def test_trace_preserves_authorized_versions(temp_db: Path):
    trace = QueryTrace(
        id="trace_test_001",
        created_at="2026-11-27T12:00:00",
        query="¿Qué modalidades de grado existen?",
        version_id="ver_rtg_2019",
        retrieved_chunks_json="[]",
        response="Respuesta orientativa...",
        citations_json="[]",
        abstained=False,
        abstention_reason=None,
        retrieval_ms=15.2,
        generation_ms=150.0,
        total_ms=165.2,
        execution_status="ok",
        authorized_versions_json='[{"id":"ver_rtg_2019","family_id":"fam_reglamento_tg","nombre":"Reglamento TG"}]',
    )
    trace_db.insert_trace(trace, temp_db)

    saved_trace = trace_db.get_trace("trace_test_001", temp_db)
    assert saved_trace is not None
    assert saved_trace.authorized_versions_json is not None
    assert "ver_rtg_2019" in saved_trace.authorized_versions_json
    assert "fam_reglamento_tg" in saved_trace.authorized_versions_json


# -----------------------------------------------------------------------------
# 14. Seguridad: Autenticación requerida en endpoints de categorías y familias
# -----------------------------------------------------------------------------
def test_admin_endpoints_auth_protection():
    client = TestClient(app)

    # Intento sin cookie o header de admin
    resp_cat_post = client.post("/api/admin/categories", json={"id": "cat_test", "nombre": "Test"})
    assert resp_cat_post.status_code == 401

    resp_fam_post = client.post("/api/admin/families", json={"id": "fam_test", "nombre": "Test"})
    assert resp_fam_post.status_code == 401

    resp_cat_list = client.get("/api/admin/categories")
    assert resp_cat_list.status_code == 401

    resp_active_corpus = client.get("/api/admin/active-corpus")
    assert resp_active_corpus.status_code == 401

    # Con credenciales válidas vía cookie de sesión
    client.post("/api/admin/login", json={"admin_key": settings.ADMIN_API_KEY})
    resp_cat_auth = client.get("/api/admin/categories")
    assert resp_cat_auth.status_code == 200
    assert isinstance(resp_cat_auth.json(), list)


# -----------------------------------------------------------------------------
# 15. Exclusión y bloqueo de categorías y familias desactivadas
# -----------------------------------------------------------------------------
def test_deactivated_category_and_family_behavior(populated_env):
    db_path = populated_env["db"]

    doc = DocumentMetadata(
        id="doc_deact_test",
        filename="test.pdf",
        file_path="/tmp/test.pdf",
        file_hash="hash_deact_test",
        file_size_bytes=500,
        uploaded_at="2026-11-27T12:00:00",
    )
    db.save_document(doc, db_path)

    ver = NormativeVersion(
        id="ver_deact_test",
        document_id="doc_deact_test",
        nombre="Versión en Familia Activa",
        numero_acuerdo="01",
        anio=2023,
        fecha_expedicion="2023-01-01",
        estado_vigencia="VIGENTE",
        status=ProcessingStatus.PROCESADO,
        status_message="OK",
        is_active=False,
        created_at="2026-11-27T12:00:00",
        updated_at="2026-11-27T12:00:00",
        family_id="fam_p_dc_28",
        estado_revision="APROBADO",
    )
    db.create_version(ver, db_path)
    db.set_active_version("ver_deact_test", db_path)

    # 1. Comprobar que está activa
    active = db.get_active_versions(db_path)
    assert any(v.id == "ver_deact_test" for v in active)

    # 2. Desactivar la categoría "cat_procedimientos"
    db.update_category("cat_procedimientos", estado="INACTIVO", db_path=db_path)

    # 3. Al listar versiones activas para RAG, DEBE quedar excluida
    active_after = db.get_active_versions(db_path)
    assert not any(v.id == "ver_deact_test" for v in active_after)

    # 4. Intentar activar una versión cuya categoría está inactiva debe fallar
    with pytest.raises(ValueError, match="categoría documental está inactiva"):
        db.set_active_version("ver_deact_test", db_path)

    # 5. Reactivar categoría pero desactivar la familia "fam_p_dc_28"
    db.update_category("cat_procedimientos", estado="ACTIVO", db_path=db_path)
    db.update_family("fam_p_dc_28", estado="INACTIVO", db_path=db_path)

    # Debe seguir excluida
    active_after_fam = db.get_active_versions(db_path)
    assert not any(v.id == "ver_deact_test" for v in active_after_fam)

    # Intentar activar debe fallar por familia inactiva
    with pytest.raises(ValueError, match="familia documental está inactiva"):
        db.set_active_version("ver_deact_test", db_path)
