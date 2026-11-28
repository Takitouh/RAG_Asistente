from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from normativa.config import settings
from normativa.corpus import db
from normativa.corpus.models import (
    DocumentCategory,
    DocumentFamily,
    DocumentMetadata,
    NormativeVersion,
    ProcessingStatus,
)
from normativa.ingestion.extractor import extract_pages
from normativa.retrieval.indexer import QdrantCorpusIndexer


class CorpusService:
    def __init__(
        self,
        db_path: str | Path | None = None,
        indexer: QdrantCorpusIndexer | None = None,
    ) -> None:
        self.db_path = Path(db_path) if db_path else Path(settings.SQLITE_PATH)
        self.indexer = indexer or QdrantCorpusIndexer()
        db.init_db(self.db_path)

    def register_document(
        self,
        file_bytes: bytes,
        filename: str,
        version_id: str,
        nombre: str,
        family_id: str = "fam_reglamento_tg",
        numero_version_institucional: str | None = None,
        numero_acuerdo: str | None = None,
        anio: int | None = None,
        fecha_expedicion: str | None = None,
        procedencia: str | None = None,
        estado_vigencia: str | None = None,
    ) -> tuple[DocumentMetadata, NormativeVersion]:
        # Validar version_id único
        existing_version = db.get_version(version_id, db_path=self.db_path)
        if existing_version is not None:
            raise ValueError(f"Ya existe una versión normativa con el identificador '{version_id}'")

        if not file_bytes:
            raise ValueError("El archivo PDF recibido está vacío (0 bytes)")

        # Validar familia existente
        family = db.get_family(family_id, db_path=self.db_path)
        if family is None:
            raise ValueError(f"La familia documental '{family_id}' no existe.")

        # Calcular SHA-256
        sha256 = hashlib.sha256(file_bytes).hexdigest()

        # Detección de duplicados SHA-256 y control de discrepancias de identidad (Reglas 11 y 15)
        duplicates = db.detect_sha256_duplicates(sha256, db_path=self.db_path)
        inconsistencia = False
        estado_revision = "PENDIENTE"
        status_message = "Documento recibido y registrado. Pendiente de procesamiento."

        if duplicates:
            # Si ya existe un documento con este mismo hash
            for dup in duplicates:
                dup_ver_id = dup.get("version_id")
                dup_acuerdo = dup.get("numero_acuerdo")
                dup_anio = dup.get("anio")
                dup_family = dup.get("family_id")

                # Si el documento existente tiene distinto acuerdo o año declarado
                if (dup_acuerdo and numero_acuerdo and dup_acuerdo.strip() != numero_acuerdo.strip()) or \
                   (dup_anio and anio and dup_anio != anio) or \
                   (dup_family and dup_family != family_id):
                    inconsistencia = True
                    estado_revision = "CON_DISCREPANCIAS"
                    status_message = (
                        f"Advertencia de discrepancia documental: El archivo PDF tiene una huella SHA-256 "
                        f"idéntica a la versión '{dup_ver_id}', pero se declararon metadatos normativos diferentes. "
                        f"No se permite activar hasta aclarar la identidad oficial."
                    )
                    break
            if not inconsistencia:
                status_message = f"Archivo cargado. Nota: Huella SHA-256 coincide con documento previo ({len(duplicates)} coincidencia(s))."

        # Guardar archivo PDF en directorio de PDFs
        pdf_dir = Path(settings.DATA_DIR) / "pdfs"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{version_id}_{filename}"
        dest_path = pdf_dir / safe_filename
        dest_path.write_bytes(file_bytes)

        now = datetime.now(timezone.utc).isoformat()
        doc_id = f"doc_{uuid.uuid4().hex[:10]}"

        document = DocumentMetadata(
            id=doc_id,
            filename=filename,
            file_path=str(dest_path),
            file_hash=sha256,
            file_size_bytes=len(file_bytes),
            uploaded_at=now,
        )
        db.save_document(document, db_path=self.db_path)

        version = NormativeVersion(
            id=version_id,
            document_id=doc_id,
            family_id=family_id,
            nombre=nombre,
            numero_version_institucional=numero_version_institucional,
            numero_acuerdo=numero_acuerdo,
            anio=anio,
            fecha_expedicion=fecha_expedicion,
            procedencia=procedencia,
            estado_vigencia=estado_vigencia,
            status=ProcessingStatus.RECIBIDO,
            status_message=status_message,
            estado_revision=estado_revision,
            fecha_revision=None,
            observaciones_revision=None,
            inconsistencia_identidad=inconsistencia,
            is_active=False,
            created_at=now,
            updated_at=now,
            activated_at=None,
            report_json=None,
            chunks_count=0,
            file_hash=sha256,
            family_name=family.nombre,
            categoria_id=family.categoria_id,
            categoria_nombre=family.categoria_nombre,
        )
        db.save_version(version, db_path=self.db_path)

        return document, version

    def process_and_index_version(
        self,
        version_id: str,
        force_ocr: bool = False,
        embed_fn: Callable[[str], list[float]] | None = None,
        skip_vector_index: bool = False,
        expected_articles_count: int | None = None,
    ) -> NormativeVersion:
        version = db.get_version(version_id, db_path=self.db_path)
        if version is None:
            raise ValueError(f"No existe la versión normativa '{version_id}'")

        doc = db.get_document(version.document_id, db_path=self.db_path)
        if doc is None:
            raise ValueError(f"No se encontró el documento asociado a la versión '{version_id}'")

        pdf_path = Path(doc.file_path)
        if not pdf_path.exists():
            raise FileNotFoundError(f"No se encuentra el archivo PDF en disco: {pdf_path}")

        family = db.get_family(version.family_id, db_path=self.db_path)
        categoria_id = family.categoria_id if family else None
        profile_str = family.perfil_procesamiento if family else "reglamento_estructurado"

        # Marcar EN_PROCESAMIENTO
        db.update_version_status(
            version_id,
            ProcessingStatus.EN_PROCESAMIENTO,
            message="Iniciando extracción y procesamiento documental...",
            db_path=self.db_path,
        )

        try:
            # Lazy imports para evitar import circular con corpus/__init__.py
            from normativa.ingestion.profiles import get_processor, DocumentProfile  # noqa: PLC0415
            from normativa.ingestion.quality.checker import QualityChecker  # noqa: PLC0415

            # 1. Extracción por página (híbrida: capa de texto → OCR por fallback)
            pages = extract_pages(pdf_path, force_ocr=force_ocr)
            if not pages:
                raise ValueError("No se pudo extraer texto de ninguna página del documento")

            # 2. Seleccionar procesador según perfil de la familia documental
            try:
                profile_enum = DocumentProfile(profile_str)
            except ValueError:
                profile_enum = DocumentProfile.DOCUMENTO_GENERAL

            processor = get_processor(profile_enum)
            processing_result = processor.process(
                pdf_path=pdf_path,
                pages=pages,
                version_id=version_id,
                document_id=doc.id,
                document_name=doc.filename,
                categoria_id=categoria_id,
                family_id=version.family_id,
                expected_articles_count=expected_articles_count,
            )

            chunks = processing_result.chunks
            report_data = processing_result.report
            report_data["profile_used"] = profile_enum.value
            report_data["num_pages"] = len(pages)
            report_data["extraction_methods"] = {
                "text_layer": sum(1 for p in pages if p.method == "text_layer"),
                "ocr": sum(1 for p in pages if p.method == "ocr"),
            }
            # Confianza media OCR
            ocr_confidences = [p.ocr_confidence for p in pages if p.ocr_confidence is not None]
            report_data["ocr_confidence_mean"] = (
                sum(ocr_confidences) / len(ocr_confidences) if ocr_confidences else None
            )

            if not chunks:
                raise ValueError("El procesamiento no produjo ningún chunk normativo válido")

            # 3. Controles de calidad
            checker = QualityChecker(qdrant_indexer=None)  # Qdrant se chequea post-index
            declared_meta = {
                "numero_acuerdo": version.numero_acuerdo,
                "anio": version.anio,
            }
            quality_report = checker.check(
                version_id=version_id,
                document_name=doc.filename,
                profile=profile_enum,
                pages=pages,
                processing_report=report_data,
                processing_metadata=processing_result.metadata,
                declared_metadata=declared_meta,
                db_chunks_count=None,  # Aún no guardados
            )
            report_data["quality_report"] = quality_report.to_dict()

            # 4. Guardar chunks en SQLite
            db.delete_chunks_by_version(version_id, db_path=self.db_path)
            db.insert_chunks(chunks, db_path=self.db_path)

            # 5. Indexación en Qdrant
            if not skip_vector_index:
                self.indexer.index_chunks(
                    version_id=version_id,
                    chunks=chunks,
                    embed_fn=embed_fn,
                )
                # Verificación de correspondencia SQLite ↔ Qdrant post-indexación
                try:
                    qdrant_count = self.indexer.count_version_points(version_id)
                    sqlite_count = len(chunks)
                    report_data["qdrant_sqlite_correspondence"] = {
                        "sqlite_chunks": sqlite_count,
                        "qdrant_points": qdrant_count,
                        "coincide": qdrant_count == sqlite_count,
                    }
                    if qdrant_count != sqlite_count:
                        from normativa.ingestion.quality.checker import QualityIssue, IssueSeverity  # noqa: PLC0415
                        quality_report.issues.append(
                            QualityIssue(
                                code="QDRANT_SQLITE_MISMATCH",
                                severity=IssueSeverity.CRITICAL,
                                message=f"SQLite={sqlite_count} ≠ Qdrant={qdrant_count} para versión '{version_id}'.",
                            )
                        )
                except Exception:
                    pass

            # 6. Decidir estado final
            blocks_activation = quality_report.blocks_activation or version.inconsistencia_identidad
            if blocks_activation:
                final_status = ProcessingStatus.PENDIENTE_REVISION
                final_msg = (
                    f"Procesado con {len(quality_report.critical_issues)} problema(s) crítico(s). "
                    "Requiere revisión previa a activación."
                )
            else:
                has_warnings = len(quality_report.warning_issues) > 0
                if has_warnings:
                    final_status = ProcessingStatus.PENDIENTE_REVISION
                    final_msg = (
                        f"Procesado con {len(quality_report.warning_issues)} advertencia(s). "
                        f"Generados {len(chunks)} fragmentos. Revisar antes de activar."
                    )
                else:
                    final_status = ProcessingStatus.PROCESADO
                    final_msg = f"Procesado e indexado exitosamente ({len(chunks)} fragmentos generados)."

            db.update_version_status(
                version_id=version_id,
                status=final_status,
                message=final_msg,
                report_json=json.dumps(report_data, ensure_ascii=False, default=str),
                chunks_count=len(chunks),
                db_path=self.db_path,
            )

            updated = db.get_version(version_id, db_path=self.db_path)
            assert updated is not None
            return updated

        except Exception as exc:
            try:
                self.indexer.delete_version_points(version_id)
            except Exception:
                pass
            db.update_version_status(
                version_id,
                ProcessingStatus.ERROR,
                message=f"Fallo en procesamiento: {exc}",
                db_path=self.db_path,
            )
            raise

    def activate_version(self, version_id: str) -> NormativeVersion:
        # Verificar que no haya problemas críticos antes de activar
        version = db.get_version(version_id, db_path=self.db_path)
        if version is None:
            raise ValueError(f"Versión '{version_id}' no encontrada.")
        if version.inconsistencia_identidad:
            raise ValueError(
                f"No se puede activar la versión '{version_id}': tiene discrepancias de identidad documentadas."
            )
        if version.report_json:
            try:
                rpt = json.loads(version.report_json)
                quality = rpt.get("quality_report", {})
                if quality.get("blocks_activation", False):
                    criticals = [
                        i["message"] for i in quality.get("issues", [])
                        if i.get("severity") == "CRITICAL"
                    ]
                    raise ValueError(
                        f"Activación bloqueada por {len(criticals)} problema(s) crítico(s): "
                        + "; ".join(criticals[:3])
                    )
            except (json.JSONDecodeError, KeyError):
                pass
        db.activate_version(version_id, db_path=self.db_path)
        version = db.get_version(version_id, db_path=self.db_path)
        assert version is not None
        return version

    def deactivate_version(self, version_id: str) -> NormativeVersion:
        db.deactivate_version(version_id, db_path=self.db_path)
        version = db.get_version(version_id, db_path=self.db_path)
        assert version is not None
        return version

    def get_active_version(self) -> NormativeVersion | None:
        return db.get_active_version(db_path=self.db_path)

    def get_active_versions(self) -> list[NormativeVersion]:
        return db.get_active_versions(db_path=self.db_path)

    def get_active_version_by_family(self, family_id: str) -> NormativeVersion | None:
        return db.get_active_version_by_family(family_id, db_path=self.db_path)

    def delete_version(self, version_id: str) -> bool:
        deleted = db.delete_version(version_id, db_path=self.db_path)
        if deleted:
            try:
                self.indexer.delete_version_points(version_id)
            except Exception:
                pass
        return deleted

    def get_processing_report(self, version_id: str) -> dict[str, Any] | None:
        """Devuelve el informe de procesamiento de una versión."""
        version = db.get_version(version_id, db_path=self.db_path)
        if version is None or not version.report_json:
            return None
        try:
            return json.loads(version.report_json)
        except json.JSONDecodeError:
            return None
