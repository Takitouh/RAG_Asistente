from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, File, Form, Header, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from normativa.config import settings
from normativa.corpus import db
from normativa.corpus.models import DocumentCategory, DocumentFamily, ProcessingStatus
from normativa.corpus.service import CorpusService


admin_router = APIRouter(prefix="/api/admin", tags=["Administración del Corpus"])
public_versions_router = APIRouter(prefix="/api/versions", tags=["Versiones Normativas"])


# ---------------------------------------------------------------------------
# Schemas Pydantic
# ---------------------------------------------------------------------------

class AdminLoginRequest(BaseModel):
    admin_key: str


class ReviewVersionRequest(BaseModel):
    action: str = Field(..., description="'approve' o 'reject'")
    notes: str | None = None


class CategoryCreateRequest(BaseModel):
    id: str = Field(..., min_length=2, max_length=50)
    nombre: str = Field(..., min_length=2, max_length=100)
    descripcion: str | None = None
    estado: str = Field("ACTIVO", description="'ACTIVO' o 'INACTIVO'")


class CategoryUpdateRequest(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    estado: str | None = None


class FamilyCreateRequest(BaseModel):
    id: str = Field(..., min_length=2, max_length=50)
    categoria_id: str = Field(..., min_length=2, max_length=50)
    codigo: str = Field(..., min_length=1, max_length=30)
    nombre: str = Field(..., min_length=2, max_length=150)
    descripcion: str | None = None
    perfil_procesamiento: str = Field("reglamento_estructurado", description="Perfil de procesamiento técnico")
    estado: str = Field("ACTIVO", description="'ACTIVO' o 'INACTIVO'")


class FamilyUpdateRequest(BaseModel):
    categoria_id: str | None = None
    codigo: str | None = None
    nombre: str | None = None
    descripcion: str | None = None
    perfil_procesamiento: str | None = None
    estado: str | None = None


# ---------------------------------------------------------------------------
# Dependencias y Autenticación
# ---------------------------------------------------------------------------

def verify_admin_key(
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
    admin_session: Annotated[str | None, Cookie()] = None,
) -> bool:
    expected_key = settings.ADMIN_API_KEY
    provided_key = None

    if x_admin_key:
        provided_key = x_admin_key
    elif authorization and authorization.startswith("Bearer "):
        provided_key = authorization.split("Bearer ", 1)[1].strip()
    elif admin_session:
        provided_key = admin_session

    if not provided_key or provided_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credencial administrativa inválida o ausente (use header X-Admin-Key o Bearer token)",
        )
    return True


def get_corpus_service() -> CorpusService:
    return CorpusService()


# ---------------------------------------------------------------------------
# Endpoints Públicos
# ---------------------------------------------------------------------------

@public_versions_router.get("/active")
def get_active_version_public(
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    active = service.get_active_version()
    active_corpus = service.get_active_versions()
    has_active = len(active_corpus) > 0

    if not has_active:
        return {
            "active_version": None,
            "has_active_version": False,
            "active_corpus": [],
            "message": "No hay ninguna versión normativa activa actualmente.",
        }

    return {
        "active_version": active.to_dict() if active else None,
        "has_active_version": True,
        "active_corpus": [v.to_dict() for v in active_corpus],
        "message": f"Corpus activo: {len(active_corpus)} documento(s) institucional(es) habilitado(s).",
    }


@public_versions_router.get("/{version_id}/pdf")
def get_version_pdf(
    version_id: str,
    service: CorpusService = Depends(get_corpus_service),
):
    version = db.get_version(version_id, service.db_path)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la versión con ID '{version_id}'",
        )
    doc = db.get_document(version.document_id, service.db_path)
    if doc is None or not doc.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento no encontrado para esta versión",
        )
    file_path = Path(doc.file_path).resolve()
    base_dir = Path(settings.DATA_DIR).resolve()
    if not file_path.is_relative_to(base_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado al archivo por política de seguridad",
        )
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El archivo PDF no fue encontrado en el almacenamiento local",
        )
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=doc.filename,
    )


# ---------------------------------------------------------------------------
# Endpoints Administrativos de Sesión
# ---------------------------------------------------------------------------

@admin_router.post("/login")
def admin_login(payload: AdminLoginRequest, response: Response) -> dict:
    if payload.admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clave administrativa incorrecta",
        )
    response.set_cookie(
        key="admin_session",
        value=settings.ADMIN_API_KEY,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=86400,
        path="/",
    )
    return {
        "success": True,
        "message": "Autenticación exitosa",
        "token": settings.ADMIN_API_KEY,
    }


@admin_router.post("/logout")
def admin_logout(response: Response) -> dict:
    response.delete_cookie(
        key="admin_session",
        path="/",
        httponly=True,
        samesite="lax",
    )
    return {"success": True, "message": "Sesión administrativa cerrada"}


@admin_router.get("/me")
def admin_me(_: bool = Depends(verify_admin_key)) -> dict:
    return {"authenticated": True, "role": "admin"}


@admin_router.get("/stats")
def get_admin_stats(
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    categories = db.list_categories(include_inactive=True, db_path=service.db_path)
    families = db.list_families(include_inactive=True, db_path=service.db_path)
    versions = db.list_versions(db_path=service.db_path)
    active = service.get_active_version()
    active_corpus = service.get_active_versions()

    status_counts = {
        ProcessingStatus.RECIBIDO.value: 0,
        ProcessingStatus.EN_PROCESAMIENTO.value: 0,
        ProcessingStatus.PENDIENTE_REVISION.value: 0,
        ProcessingStatus.PROCESADO.value: 0,
        ProcessingStatus.ERROR.value: 0,
    }
    total_chunks = 0
    active_chunks = sum(v.chunks_count for v in active_corpus)
    inconsistent_count = 0
    for v in versions:
        s = v.status.value if isinstance(v.status, ProcessingStatus) else str(v.status)
        status_counts[s] = status_counts.get(s, 0) + 1
        total_chunks += v.chunks_count
        if v.inconsistencia_identidad:
            inconsistent_count += 1

    trace_count = 0
    try:
        with db.get_connection(service.db_path) as conn:
            row = conn.execute("SELECT count(*) FROM traces").fetchone()
            if row:
                trace_count = row[0]
    except Exception:
        pass

    return {
        "total_categories": len(categories),
        "total_families": len(families),
        "total_versions": len(versions),
        "status_counts": status_counts,
        "active_version": active.to_dict() if active else None,
        "active_corpus": [v.to_dict() for v in active_corpus],
        "total_chunks": total_chunks,
        "active_chunks": active_chunks,
        "total_traces": trace_count,
        "inconsistent_versions_count": inconsistent_count,
    }


# ---------------------------------------------------------------------------
# Gestión de Categorías Documentales (CRUD)
# ---------------------------------------------------------------------------

@admin_router.get("/categories")
def list_categories_admin(
    include_inactive: bool = True,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> list[dict]:
    cats = db.list_categories(include_inactive=include_inactive, db_path=service.db_path)
    return [c.to_dict() for c in cats]


@admin_router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category_admin(
    payload: CategoryCreateRequest,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    existing = db.get_category(payload.id, db_path=service.db_path)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una categoría documental con ID '{payload.id}'",
        )
    cat = DocumentCategory(
        id=payload.id.strip(),
        nombre=payload.nombre.strip(),
        descripcion=payload.descripcion.strip() if payload.descripcion else None,
        estado=payload.estado.strip().upper(),
    )
    saved = db.save_category(cat, db_path=service.db_path)
    return saved.to_dict()


@admin_router.get("/categories/{cat_id}")
def get_category_admin(
    cat_id: str,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    cat = db.get_category(cat_id, db_path=service.db_path)
    if not cat:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Categoría '{cat_id}' no encontrada")
    return cat.to_dict()


@admin_router.put("/categories/{cat_id}")
def update_category_admin(
    cat_id: str,
    payload: CategoryUpdateRequest,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    try:
        updated = db.update_category(
            cat_id=cat_id,
            nombre=payload.nombre,
            descripcion=payload.descripcion,
            estado=payload.estado,
            db_path=service.db_path,
        )
        return updated.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@admin_router.delete("/categories/{cat_id}")
def delete_category_admin(
    cat_id: str,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    try:
        deleted = db.delete_category(cat_id, db_path=service.db_path)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Categoría '{cat_id}' no encontrada")
        return {"success": True, "message": f"Categoría '{cat_id}' eliminada correctamente"}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Gestión de Familias Documentales (CRUD)
# ---------------------------------------------------------------------------

@admin_router.get("/families")
def list_families_admin(
    categoria_id: str | None = None,
    include_inactive: bool = True,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> list[dict]:
    fams = db.list_families(categoria_id=categoria_id, include_inactive=include_inactive, db_path=service.db_path)
    return [f.to_dict() for f in fams]


@admin_router.post("/families", status_code=status.HTTP_201_CREATED)
def create_family_admin(
    payload: FamilyCreateRequest,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    existing = db.get_family(payload.id, db_path=service.db_path)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe una familia documental con ID '{payload.id}'",
        )
    cat = db.get_category(payload.categoria_id, db_path=service.db_path)
    if not cat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"La categoría '{payload.categoria_id}' no existe",
        )
    fam = DocumentFamily(
        id=payload.id.strip(),
        categoria_id=payload.categoria_id.strip(),
        codigo=payload.codigo.strip(),
        nombre=payload.nombre.strip(),
        descripcion=payload.descripcion.strip() if payload.descripcion else None,
        perfil_procesamiento=payload.perfil_procesamiento.strip() if payload.perfil_procesamiento else "reglamento_estructurado",
        estado=payload.estado.strip().upper(),
    )
    try:
        saved = db.save_family(fam, db_path=service.db_path)
        return saved.to_dict()
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@admin_router.get("/families/{family_id}")
def get_family_admin(
    family_id: str,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    fam = db.get_family(family_id, db_path=service.db_path)
    if not fam:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Familia '{family_id}' no encontrada")
    return fam.to_dict()


@admin_router.put("/families/{family_id}")
def update_family_admin(
    family_id: str,
    payload: FamilyUpdateRequest,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    try:
        updated = db.update_family(
            family_id=family_id,
            nombre=payload.nombre,
            codigo=payload.codigo,
            descripcion=payload.descripcion,
            categoria_id=payload.categoria_id,
            perfil_procesamiento=payload.perfil_procesamiento,
            estado=payload.estado,
            db_path=service.db_path,
        )
        return updated.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@admin_router.delete("/families/{family_id}")
def delete_family_admin(
    family_id: str,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    try:
        deleted = db.delete_family(family_id, db_path=service.db_path)
        if not deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Familia '{family_id}' no encontrada")
        return {"success": True, "message": f"Familia '{family_id}' eliminada correctamente"}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@admin_router.get("/families/{family_id}/versions")
def list_family_versions_admin(
    family_id: str,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> list[dict]:
    versions = db.list_versions(family_id=family_id, db_path=service.db_path)
    return [v.to_dict() for v in versions]


# ---------------------------------------------------------------------------
# Gestión de Versiones Documentales y Carga
# ---------------------------------------------------------------------------

@admin_router.get("/active-corpus")
def get_active_corpus_admin(
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> list[dict]:
    active_versions = service.get_active_versions()
    return [v.to_dict() for v in active_versions]


@admin_router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    version_id: str = Form(...),
    nombre: str = Form(...),
    family_id: str = Form("fam_reglamento_tg"),
    numero_version_institucional: str | None = Form(None),
    numero_acuerdo: str | None = Form(None),
    anio: int | None = Form(None),
    fecha_expedicion: str | None = Form(None),
    procedencia: str | None = Form(None),
    estado_vigencia: str | None = Form(None),
    auto_process: bool = Form(True),
    force_ocr: bool = Form(False),
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo debe ser un documento PDF válido con extensión .pdf",
        )

    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El archivo cargado está vacío (0 bytes)",
        )

    clean_version_id = version_id.strip()
    if not clean_version_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El identificador version_id no puede estar vacío",
        )

    try:
        doc, ver = service.register_document(
            file_bytes=file_bytes,
            filename=file.filename,
            version_id=clean_version_id,
            nombre=nombre.strip(),
            family_id=family_id.strip() if family_id else "fam_reglamento_tg",
            numero_version_institucional=numero_version_institucional.strip() if numero_version_institucional else None,
            numero_acuerdo=numero_acuerdo.strip() if numero_acuerdo else None,
            anio=anio,
            fecha_expedicion=fecha_expedicion.strip() if fecha_expedicion else None,
            procedencia=procedencia.strip() if procedencia else None,
            estado_vigencia=estado_vigencia.strip() if estado_vigencia else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if auto_process:
        try:
            ver = service.process_and_index_version(
                version_id=clean_version_id,
                force_ocr=force_ocr,
            )
        except Exception as exc:
            return {
                "document": doc.to_dict(),
                "version": ver.to_dict(),
                "warning": f"El documento fue registrado pero falló el procesamiento: {exc}",
            }

    warning_msg = None
    if ver.inconsistencia_identidad:
        warning_msg = ver.status_message

    return {
        "document": doc.to_dict(),
        "version": ver.to_dict(),
        "warning": warning_msg,
    }


@admin_router.get("/versions")
def list_versions_admin(
    family_id: str | None = None,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> list[dict]:
    versions = db.list_versions(family_id=family_id, db_path=service.db_path)
    return [v.to_dict() for v in versions]


@admin_router.get("/versions/{version_id}")
def get_version_admin(
    version_id: str,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    version = db.get_version(version_id, service.db_path)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la versión normativa con ID '{version_id}'",
        )
    return version.to_dict()


@admin_router.get("/versions/{version_id}/report")
def get_version_report_admin(
    version_id: str,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    version = db.get_version(version_id, service.db_path)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la versión normativa con ID '{version_id}'",
        )
    if not version.report_json:
        return {
            "version_id": version.id,
            "status": version.status.value,
            "has_report": False,
            "report": None,
            "message": "La versión aún no cuenta con un informe de procesamiento.",
        }
    return {
        "version_id": version.id,
        "status": version.status.value,
        "has_report": True,
        "report": json.loads(version.report_json),
    }


@admin_router.post("/versions/{version_id}/process")
def process_version_admin(
    version_id: str,
    force_ocr: bool = False,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    version = db.get_version(version_id, service.db_path)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la versión normativa con ID '{version_id}'",
        )
    try:
        updated = service.process_and_index_version(version_id, force_ocr=force_ocr)
        return updated.to_dict()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error durante el procesamiento: {exc}",
        ) from exc


@admin_router.post("/versions/{version_id}/activate")
def activate_version_admin(
    version_id: str,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    try:
        updated = service.activate_version(version_id)
        return {
            "success": True,
            "message": f"Versión '{version_id}' activada exitosamente para la familia documental '{updated.family_name or updated.family_id}'.",
            "version": updated.to_dict(),
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@admin_router.post("/versions/{version_id}/deactivate")
def deactivate_version_admin(
    version_id: str,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    try:
        updated = service.deactivate_version(version_id)
        return {
            "success": True,
            "message": f"Versión '{version_id}' desactivada de su familia documental.",
            "version": updated.to_dict(),
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@admin_router.patch("/versions/{version_id}/metadata")
def update_version_metadata_admin(
    version_id: str,
    nombre: str | None = None,
    numero_acuerdo: str | None = None,
    anio: int | None = None,
    fecha_expedicion: str | None = None,
    estado_vigencia: str | None = None,
    family_id: str | None = None,
    numero_version_institucional: str | None = None,
    procedencia: str | None = None,
    estado_revision: str | None = None,
    observaciones_revision: str | None = None,
    inconsistencia_identidad: bool | None = None,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    try:
        updated = db.update_version_metadata(
            version_id=version_id,
            nombre=nombre,
            numero_acuerdo=numero_acuerdo,
            anio=anio,
            fecha_expedicion=fecha_expedicion,
            estado_vigencia=estado_vigencia,
            family_id=family_id,
            numero_version_institucional=numero_version_institucional,
            procedencia=procedencia,
            estado_revision=estado_revision,
            observaciones_revision=observaciones_revision,
            inconsistencia_identidad=inconsistencia_identidad,
            db_path=service.db_path,
        )
        return {
            "success": True,
            "message": "Metadatos actualizados correctamente. Revise antes de activar la versión.",
            "version": updated.to_dict(),
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@admin_router.post("/versions/{version_id}/review")
def review_version_admin(
    version_id: str,
    payload: ReviewVersionRequest,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    version = db.get_version(version_id, service.db_path)
    if version is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No se encontró la versión normativa con ID '{version_id}'",
        )
    if payload.action == "approve":
        note_text = f"Revisión humana aprobada. {payload.notes or ''}".strip()
        db.update_version_status(
            version_id=version_id,
            status=ProcessingStatus.PROCESADO,
            message=note_text,
            estado_revision="APROBADO",
            observaciones_revision=note_text,
            inconsistencia_identidad=False,  # La aprobación humana documentada resuelve la inconsistencia
            db_path=service.db_path,
        )
    elif payload.action == "reject":
        note_text = f"Revisión humana rechazada. {payload.notes or ''}".strip()
        db.update_version_status(
            version_id=version_id,
            status=ProcessingStatus.ERROR,
            message=note_text,
            estado_revision="RECHAZADO",
            observaciones_revision=note_text,
            db_path=service.db_path,
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Acción no válida. Se espera 'approve' o 'reject'",
        )

    updated = db.get_version(version_id, service.db_path)
    assert updated is not None
    return {
        "success": True,
        "message": f"Versión '{version_id}' actualizada a estado '{updated.status.value}' y revisión '{updated.estado_revision}'",
        "version": updated.to_dict(),
    }


@admin_router.delete("/versions/{version_id}")
def delete_version_admin(
    version_id: str,
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    try:
        deleted = service.delete_version(version_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontró la versión con ID '{version_id}'",
            )
        return {
            "success": True,
            "message": f"Versión '{version_id}' y sus chunks eliminados correctamente.",
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
