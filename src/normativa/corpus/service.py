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
from normativa.corpus.chunker import build_chunks_from_parsed_document
from normativa.corpus.models import DocumentMetadata, NormativeVersion, ProcessingStatus
from normativa.ingestion.cleaner import clean_pages, render_cleaning_log
from normativa.ingestion.extractor import extract_pages, pages_to_json
from normativa.ingestion.parser import parse_document, render_parse_report
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
        numero_acuerdo: str | None = None,
        anio: int | None = None,
        fecha_expedicion: str | None = None,
        estado_vigencia: str | None = None,
    ) -> tuple[DocumentMetadata, NormativeVersion]:
        # Validar version_id único
        existing_version = db.get_version(version_id, db_path=self.db_path)
        if existing_version is not None:
            raise ValueError(f"Ya existe una versión normativa con el identificador '{version_id}'")

        if not file_bytes:
            raise ValueError("El archivo PDF recibido está vacío (0 bytes)")

        # Calcular SHA-256
        sha256 = hashlib.sha256(file_bytes).hexdigest()

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
            nombre=nombre,
            numero_acuerdo=numero_acuerdo,
            anio=anio,
            fecha_expedicion=fecha_expedicion,
            estado_vigencia=estado_vigencia,
            status=ProcessingStatus.RECIBIDO,
            status_message="Documento recibido y registrado. Pendiente de procesamiento.",
            is_active=False,
            created_at=now,
            updated_at=now,
            activated_at=None,
            report_json=None,
            chunks_count=0,
        )
        db.save_version(version, db_path=self.db_path)

        return document, version

    def process_and_index_version(
        self,
        version_id: str,
        force_ocr: bool = False,
        embed_fn: Callable[[str], list[float]] | None = None,
        skip_vector_index: bool = False,
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

        # Marcar EN_PROCESAMIENTO
        db.update_version_status(
            version_id,
            ProcessingStatus.EN_PROCESAMIENTO,
            message="Iniciando extracción y procesamiento documental...",
            db_path=self.db_path,
        )

        try:
            # 1. Extracción (capa de texto o fallback a OCR)
            pages = extract_pages(pdf_path, force_ocr=force_ocr)
            if not pages:
                raise ValueError("No se pudo extraer texto de ninguna página del documento")

            # 2. Limpieza
            clean_pages_result, cleaning_log = clean_pages(pages)

            # 3. Parseo estructural
            parsed = parse_document(clean_pages_result, source_file=str(pdf_path))

            # 4. Evaluación de anomalías y validación de calidad OCR
            ocr_confidences = [p.ocr_confidence for p in pages if p.ocr_confidence is not None]
            avg_ocr_conf = sum(ocr_confidences) / len(ocr_confidences) if ocr_confidences else None

            # Construir informe consolidado
            report_data: dict[str, Any] = {
                "num_pages": len(pages),
                "extraction_methods": {
                    "text_layer": sum(1 for p in pages if p.method == "text_layer"),
                    "ocr": sum(1 for p in pages if p.method == "ocr"),
                },
                "ocr_confidence_mean": avg_ocr_conf,
                "anomalies": parsed.report.anomalies,
                "repairs": [asdict(r) for r in parsed.report.repairs],
                "statistics": parsed.report.statistics,
                "cleaning_statistics": cleaning_log.statistics,
            }

            # 5. Generación de chunks
            chunks = build_chunks_from_parsed_document(
                parsed=parsed,
                version_id=version_id,
                document_id=doc.id,
                document_name=doc.filename,
            )

            if not chunks:
                raise ValueError("El parseo no produjo ningún chunk normativo válido")

            # Guardar chunks en SQLite
            db.delete_chunks_by_version(version_id, db_path=self.db_path)
            db.insert_chunks(chunks, db_path=self.db_path)

            # 6. Indexación en Qdrant (a menos que se omita explícitamente en tests)
            if not skip_vector_index:
                self.indexer.index_chunks(
                    version_id=version_id,
                    chunks=chunks,
                    embed_fn=embed_fn,
                )

            # 7. Decidir estado final según severidad de anomalías
            # Si hay anomalías graves (ej: confianza OCR muy baja < 75 o faltan artículos)
            has_severe_anomalies = False
            if avg_ocr_conf is not None and avg_ocr_conf < 75.0:
                has_severe_anomalies = True
            if any("Faltan artículos" in a for a in parsed.report.anomalies):
                has_severe_anomalies = True

            if has_severe_anomalies:
                final_status = ProcessingStatus.PENDIENTE_REVISION
                final_msg = "Procesado con advertencias o baja confianza OCR. Requiere revisión previa a activación."
            else:
                final_status = ProcessingStatus.PROCESADO
                final_msg = f"Procesado e indexado exitosamente ({len(chunks)} chunks generados)."

            db.update_version_status(
                version_id=version_id,
                status=final_status,
                message=final_msg,
                report_json=json.dumps(report_data, ensure_ascii=False),
                chunks_count=len(chunks),
                db_path=self.db_path,
            )

            updated = db.get_version(version_id, db_path=self.db_path)
            assert updated is not None
            return updated

        except Exception as exc:
            # En caso de fallo, marcar ERROR y limpiar vectores en Qdrant
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

    def delete_version(self, version_id: str) -> bool:
        # Elimina vectores de Qdrant y registros SQLite
        deleted = db.delete_version(version_id, db_path=self.db_path)
        if deleted:
            try:
                self.indexer.delete_version_points(version_id)
            except Exception:
                pass
        return deleted
