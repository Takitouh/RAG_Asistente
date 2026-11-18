from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, File, Form, Header, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from normativa.config import settings
from normativa.corpus import db
from normativa.corpus.models import ProcessingStatus
from normativa.corpus.service import CorpusService


admin_router = APIRouter(prefix="/api/admin", tags=["Administración del Corpus"])
public_versions_router = APIRouter(prefix="/api/versions", tags=["Versiones Normativas"])


class AdminLoginRequest(BaseModel):
    admin_key: str


class ReviewVersionRequest(BaseModel):
    action: str = Field(..., description="'approve' o 'reject'")
    notes: str | None = None


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


# --- Endpoints Públicos ---

@public_versions_router.get("/active")
def get_active_version_public(
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    active = service.get_active_version()
    if active is None:
        return {
            "active_version": None,
            "has_active_version": False,
            "message": "No hay ninguna versión normativa activa actualmente.",
        }
    return {
        "active_version": active.to_dict(),
        "has_active_version": True,
        "message": f"Versión activa: {active.nombre} (ID: {active.id})",
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


# --- Endpoints Administrativos Protegidos ---

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
    versions = db.list_versions(service.db_path)
    active = service.get_active_version()
    status_counts = {
        ProcessingStatus.RECIBIDO.value: 0,
        ProcessingStatus.EN_PROCESAMIENTO.value: 0,
        ProcessingStatus.PENDIENTE_REVISION.value: 0,
        ProcessingStatus.PROCESADO.value: 0,
        ProcessingStatus.ERROR.value: 0,
    }
    total_chunks = 0
    for v in versions:
        s = v.status.value if isinstance(v.status, ProcessingStatus) else str(v.status)
        status_counts[s] = status_counts.get(s, 0) + 1
        total_chunks += v.chunks_count

    trace_count = 0
    try:
        with db.get_connection(service.db_path) as conn:
            row = conn.execute("SELECT count(*) FROM traces").fetchone()
            if row:
                trace_count = row[0]
    except Exception:
        pass

    return {
        "total_versions": len(versions),
        "status_counts": status_counts,
        "active_version": active.to_dict() if active else None,
        "total_chunks": total_chunks,
        "total_traces": trace_count,
    }

@admin_router.post("/documents", status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    version_id: str = Form(...),
    nombre: str = Form(...),
    numero_acuerdo: str | None = Form(None),
    anio: int | None = Form(None),
    fecha_expedicion: str | None = Form(None),
    estado_vigencia: str | None = Form(None),
    auto_process: bool = Form(True),
    force_ocr: bool = Form(False),
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    # Validaciones del archivo
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

    # Validar formato de version_id
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
            numero_acuerdo=numero_acuerdo.strip() if numero_acuerdo else None,
            anio=anio,
            fecha_expedicion=fecha_expedicion.strip() if fecha_expedicion else None,
            estado_vigencia=estado_vigencia.strip() if estado_vigencia else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    # Procesamiento automático opcional
    if auto_process:
        try:
            ver = service.process_and_index_version(
                version_id=clean_version_id,
                force_ocr=force_ocr,
            )
        except Exception as exc:
            # El error queda registrado en la base de datos
            return {
                "document": doc.to_dict(),
                "version": ver.to_dict(),
                "warning": f"El documento fue registrado pero falló el procesamiento: {exc}",
            }

    return {
        "document": doc.to_dict(),
        "version": ver.to_dict(),
    }


@admin_router.get("/versions")
def list_versions_admin(
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> list[dict]:
    versions = db.list_versions(service.db_path)
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
            "message": f"Versión '{version_id}' activada exitosamente como versión global.",
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
            "message": f"Versión '{version_id}' desactivada.",
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
    _: bool = Depends(verify_admin_key),
    service: CorpusService = Depends(get_corpus_service),
) -> dict:
    """Permite al administrador corregir los metadatos de una versión antes de activarla.

    Los metadatos no se verifican automáticamente contra el contenido del PDF;
    esta corrección es explícita y queda registrada.
    Los campos omitidos (None) no se modifican.
    """
    from normativa.corpus import db as corpus_db

    try:
        updated = corpus_db.update_version_metadata(
            version_id=version_id,
            nombre=nombre,
            numero_acuerdo=numero_acuerdo,
            anio=anio,
            fecha_expedicion=fecha_expedicion,
            estado_vigencia=estado_vigencia,
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
            db_path=service.db_path,
        )
    elif payload.action == "reject":
        note_text = f"Revisión humana rechazada. {payload.notes or ''}".strip()
        db.update_version_status(
            version_id=version_id,
            status=ProcessingStatus.ERROR,
            message=note_text,
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
        "message": f"Versión '{version_id}' actualizada a estado '{updated.status.value}'",
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
