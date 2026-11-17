from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile, status

from normativa.config import settings
from normativa.corpus import db
from normativa.corpus.service import CorpusService


admin_router = APIRouter(prefix="/api/admin", tags=["Administración del Corpus"])
public_versions_router = APIRouter(prefix="/api/versions", tags=["Versiones Normativas"])


def verify_admin_key(
    x_admin_key: Annotated[str | None, Header(alias="X-Admin-Key")] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> bool:
    expected_key = settings.ADMIN_API_KEY
    provided_key = None

    if x_admin_key:
        provided_key = x_admin_key
    elif authorization and authorization.startswith("Bearer "):
        provided_key = authorization.split("Bearer ", 1)[1].strip()

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


# --- Endpoints Administrativos Protegidos ---

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
