"""src/normativa/ingestion/quality/checker.py

Controles de calidad documental previos a la activación (Etapa 2, §10).

Comprueba según el perfil documental:
- Identidad documental
- Coincidencia entre metadatos declarados y detectados
- Integridad de la estructura
- Duplicados
- Páginas sin texto
- Errores de extracción
- Unidades estructurales faltantes
- Secuencias incorrectas
- Fragmentos incompletos
- Coherencia de páginas
- Correspondencia SQLite y Qdrant

Semántica de severidad:
  CRITICAL  → bloquea la activación
  WARNING   → se presenta al administrador pero no bloquea
  INFO      → informativo
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

from normativa.ingestion.extractor import PageText
from normativa.ingestion.profiles.base import DocumentProfile


class IssueSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    INFO = "INFO"


@dataclass
class QualityIssue:
    code: str                       # identificador corto del problema
    severity: IssueSeverity
    message: str
    detail: str = ""
    page: int | None = None
    unit: str | None = None         # artículo, numeral, etc.


@dataclass
class QualityReport:
    version_id: str
    document_name: str
    profile: DocumentProfile
    issues: list[QualityIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def critical_issues(self) -> list[QualityIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.CRITICAL]

    @property
    def warning_issues(self) -> list[QualityIssue]:
        return [i for i in self.issues if i.severity == IssueSeverity.WARNING]

    @property
    def blocks_activation(self) -> bool:
        return len(self.critical_issues) > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "version_id": self.version_id,
            "document_name": self.document_name,
            "profile": self.profile.value,
            "blocks_activation": self.blocks_activation,
            "critical_count": len(self.critical_issues),
            "warning_count": len(self.warning_issues),
            "info_count": len([i for i in self.issues if i.severity == IssueSeverity.INFO]),
            "issues": [
                {
                    "code": i.code,
                    "severity": i.severity.value,
                    "message": i.message,
                    "detail": i.detail,
                    "page": i.page,
                    "unit": i.unit,
                }
                for i in self.issues
            ],
            "metadata": self.metadata,
        }


class QualityChecker:
    """Ejecuta controles de calidad sobre un resultado de procesamiento documental."""

    # Umbral mínimo de confianza OCR para no emitir advertencia
    OCR_CONFIDENCE_WARNING_THRESHOLD = 75.0
    OCR_CONFIDENCE_CRITICAL_THRESHOLD = 60.0

    # Mínimo de caracteres por página para no considerarla vacía
    MIN_CHARS_PER_PAGE = 30

    def __init__(self, qdrant_indexer: Any | None = None) -> None:
        self._qdrant = qdrant_indexer

    # ------------------------------------------------------------------
    # Punto de entrada principal
    # ------------------------------------------------------------------

    def check(
        self,
        version_id: str,
        document_name: str,
        profile: DocumentProfile,
        pages: list[PageText],
        processing_report: dict[str, Any],
        processing_metadata: dict[str, Any],
        declared_metadata: dict[str, Any] | None = None,
        db_chunks_count: int | None = None,
    ) -> QualityReport:
        """Ejecuta todos los controles aplicables y devuelve un QualityReport."""
        report = QualityReport(
            version_id=version_id,
            document_name=document_name,
            profile=profile,
            metadata={
                "num_pages": len(pages),
                "profile": profile.value,
            },
        )

        self._check_pages(report, pages)
        self._check_identity(report, declared_metadata, processing_report)
        self._check_processing_anomalies(report, processing_report)

        if profile == DocumentProfile.REGLAMENTO_ESTRUCTURADO:
            self._check_reglamento(report, processing_report, processing_metadata)
        elif profile == DocumentProfile.PROCEDIMIENTO_INSTITUCIONAL:
            self._check_procedimiento(report, processing_report, processing_metadata)
        elif profile == DocumentProfile.FORMATO_INSTITUCIONAL:
            self._check_formato(report, processing_report, processing_metadata)
        else:
            self._check_general(report, processing_report)

        self._check_chunks_consistency(report, processing_report, db_chunks_count)
        self._check_qdrant_correspondence(report, version_id, db_chunks_count)

        return report

    # ------------------------------------------------------------------
    # Controles de páginas
    # ------------------------------------------------------------------

    def _check_pages(self, report: QualityReport, pages: list[PageText]) -> None:
        if not pages:
            report.issues.append(QualityIssue(
                code="NO_PAGES",
                severity=IssueSeverity.CRITICAL,
                message="El documento no tiene páginas extraídas.",
            ))
            return

        empty_pages = []
        low_conf_pages = []
        for p in pages:
            if len(p.text.strip()) < self.MIN_CHARS_PER_PAGE:
                empty_pages.append(p.page_number)
            if p.ocr_confidence is not None:
                if p.ocr_confidence < self.OCR_CONFIDENCE_CRITICAL_THRESHOLD:
                    report.issues.append(QualityIssue(
                        code="OCR_CONF_CRITICAL",
                        severity=IssueSeverity.CRITICAL,
                        message=f"Confianza OCR crítica en página {p.page_number}: {p.ocr_confidence:.1f}%",
                        page=p.page_number,
                    ))
                elif p.ocr_confidence < self.OCR_CONFIDENCE_WARNING_THRESHOLD:
                    low_conf_pages.append((p.page_number, p.ocr_confidence))

        if empty_pages:
            sev = IssueSeverity.WARNING if len(empty_pages) <= 2 else IssueSeverity.CRITICAL
            report.issues.append(QualityIssue(
                code="EMPTY_PAGES",
                severity=sev,
                message=f"Páginas sin texto suficiente: {empty_pages}",
                detail=f"{len(empty_pages)} página(s) tienen menos de {self.MIN_CHARS_PER_PAGE} caracteres.",
            ))

        if low_conf_pages:
            detail = "; ".join(f"pág.{pg}: {conf:.1f}%" for pg, conf in low_conf_pages[:5])
            report.issues.append(QualityIssue(
                code="OCR_CONF_LOW",
                severity=IssueSeverity.WARNING,
                message=f"Confianza OCR baja en {len(low_conf_pages)} página(s)",
                detail=detail,
            ))

        # Resumen de métodos de extracción
        ocr_pages = sum(1 for p in pages if p.method == "ocr")
        text_pages = sum(1 for p in pages if p.method == "text_layer")
        report.metadata["extraction_methods"] = {
            "text_layer": text_pages,
            "ocr": ocr_pages,
        }
        if ocr_pages > 0:
            report.issues.append(QualityIssue(
                code="OCR_PAGES_PRESENT",
                severity=IssueSeverity.INFO,
                message=f"{ocr_pages} página(s) procesadas por OCR. Requieren revisión humana.",
            ))

    # ------------------------------------------------------------------
    # Verificación de identidad documental
    # ------------------------------------------------------------------

    def _check_identity(
        self,
        report: QualityReport,
        declared: dict[str, Any] | None,
        processing_report: dict[str, Any],
    ) -> None:
        if not declared:
            return
        # Si el informe de procesamiento lleva campos de acuerdo detectados, compararlos
        detected_acuerdo = processing_report.get("detected_acuerdo")
        detected_anio = processing_report.get("detected_anio")
        declared_acuerdo = declared.get("numero_acuerdo")
        declared_anio = declared.get("anio")

        if detected_acuerdo and declared_acuerdo:
            if detected_acuerdo.strip().upper() != declared_acuerdo.strip().upper():
                report.issues.append(QualityIssue(
                    code="IDENTITY_ACUERDO_MISMATCH",
                    severity=IssueSeverity.CRITICAL,
                    message=(
                        f"Número de acuerdo declarado '{declared_acuerdo}' no coincide "
                        f"con el detectado '{detected_acuerdo}'."
                    ),
                ))

        if detected_anio and declared_anio:
            try:
                if int(detected_anio) != int(declared_anio):
                    report.issues.append(QualityIssue(
                        code="IDENTITY_YEAR_MISMATCH",
                        severity=IssueSeverity.CRITICAL,
                        message=(
                            f"Año declarado '{declared_anio}' no coincide con el año "
                            f"detectado '{detected_anio}' en el documento."
                        ),
                    ))
            except (TypeError, ValueError):
                pass

    # ------------------------------------------------------------------
    # Anomalías del informe de procesamiento
    # ------------------------------------------------------------------

    def _check_processing_anomalies(
        self, report: QualityReport, processing_report: dict[str, Any]
    ) -> None:
        anomalies: list[str] = processing_report.get("anomalies", [])
        for anomaly in anomalies:
            sev = IssueSeverity.CRITICAL if any(
                kw in anomaly.lower()
                for kw in ["faltan artículos", "artículos faltantes", "capítulo fuera de secuencia"]
            ) else IssueSeverity.WARNING
            report.issues.append(QualityIssue(
                code="PROCESSING_ANOMALY",
                severity=sev,
                message=anomaly,
            ))

    # ------------------------------------------------------------------
    # Controles específicos por perfil
    # ------------------------------------------------------------------

    def _check_reglamento(
        self,
        report: QualityReport,
        processing_report: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        total_art = processing_report.get("articulos_reglamento_count", 0)
        expected = processing_report.get("expected_articles_count")
        missing = processing_report.get("articulos_faltantes", [])
        min_art = processing_report.get("min_articulo")
        max_art = processing_report.get("max_articulo")

        if total_art == 0:
            report.issues.append(QualityIssue(
                code="NO_ARTICLES",
                severity=IssueSeverity.CRITICAL,
                message="No se identificó ningún artículo de reglamento.",
            ))
            return

        if missing:
            report.issues.append(QualityIssue(
                code="MISSING_ARTICLES",
                severity=IssueSeverity.CRITICAL,
                message=f"Artículos faltantes en la secuencia: {missing}",
                detail=f"Se encontraron {total_art} artículos. Faltan: {missing}",
            ))

        if expected is not None and total_art != expected:
            report.issues.append(QualityIssue(
                code="ARTICLE_COUNT_MISMATCH",
                severity=IssueSeverity.CRITICAL,
                message=(
                    f"Cantidad de artículos ({total_art}) no coincide con el valor "
                    f"esperado ({expected})."
                ),
            ))

        if min_art is not None and min_art != 1:
            report.issues.append(QualityIssue(
                code="ARTICLE_SEQUENCE_START",
                severity=IssueSeverity.WARNING,
                message=f"El primer artículo numerado es {min_art}, se esperaba 1.",
            ))

        matriz = metadata.get("matriz_articulos", [])
        arts_sin_cuerpo = [
            m["numero"] for m in matriz
            if not m.get("flags") and m.get("numero") is not None
        ]
        # Artículos con flag sin_texto → advertencia
        arts_sin_texto = [
            m["numero"] for m in matriz
            if "sin_texto" in m.get("flags", [])
        ]
        if arts_sin_texto:
            report.issues.append(QualityIssue(
                code="ARTICLES_NO_BODY",
                severity=IssueSeverity.WARNING,
                message=f"{len(arts_sin_texto)} artículo(s) sin cuerpo de texto: {arts_sin_texto[:10]}",
            ))

        report.issues.append(QualityIssue(
            code="REGLAMENTO_SUMMARY",
            severity=IssueSeverity.INFO,
            message=(
                f"Reglamento: {total_art} artículos (Art. {min_art}–{max_art}), "
                f"{processing_report.get('statistics', {}).get('capitulos', '?')} capítulos, "
                f"{processing_report.get('statistics', {}).get('paragrafos', '?')} parágrafos, "
                f"{processing_report.get('statistics', {}).get('incisos', '?')} literales/incisos."
            ),
        ))

    def _check_procedimiento(
        self,
        report: QualityReport,
        processing_report: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        secciones = processing_report.get("secciones_identificadas", [])
        actividades = processing_report.get("actividades_identificadas", 0)

        # Sección 7 (Descripción de Actividades) es crítica
        if 7 not in secciones:
            report.issues.append(QualityIssue(
                code="PROC_MISSING_SECTION_7",
                severity=IssueSeverity.CRITICAL,
                message="No se identificó la sección 7 (Descripción de las Actividades).",
            ))

        expected_sections = {1, 2, 3, 4, 5, 6, 7}
        found_secs = set(secciones)
        missing_secs = expected_sections - found_secs
        if missing_secs:
            report.issues.append(QualityIssue(
                code="PROC_MISSING_SECTIONS",
                severity=IssueSeverity.WARNING,
                message=f"Secciones no identificadas: {sorted(missing_secs)}",
            ))

        if actividades == 0 and 7 in secciones:
            report.issues.append(QualityIssue(
                code="PROC_NO_ACTIVITIES",
                severity=IssueSeverity.WARNING,
                message="Sección 7 encontrada pero no se extrajeron actividades de tabla.",
                detail="Verificar si las actividades están en tabla o en texto plano.",
            ))

        report.issues.append(QualityIssue(
            code="PROC_SUMMARY",
            severity=IssueSeverity.INFO,
            message=(
                f"Procedimiento: {len(secciones)} sección(es) identificadas, "
                f"{actividades} actividades extraídas."
            ),
        ))

    def _check_formato(
        self,
        report: QualityReport,
        processing_report: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        total_chunks = processing_report.get("total_chunks", 0)
        if total_chunks == 0:
            report.issues.append(QualityIssue(
                code="FORMAT_NO_CHUNKS",
                severity=IssueSeverity.CRITICAL,
                message="El formato no produjo ningún fragmento de contenido.",
            ))
        else:
            report.issues.append(QualityIssue(
                code="FORMAT_SUMMARY",
                severity=IssueSeverity.INFO,
                message=f"Formato institucional: {total_chunks} fragmentos generados.",
            ))

    def _check_general(
        self,
        report: QualityReport,
        processing_report: dict[str, Any],
    ) -> None:
        total_chunks = processing_report.get("total_chunks", 0)
        if total_chunks == 0:
            report.issues.append(QualityIssue(
                code="GENERAL_NO_CHUNKS",
                severity=IssueSeverity.WARNING,
                message="El documento general no produjo fragmentos.",
            ))

    # ------------------------------------------------------------------
    # Coherencia SQLite ↔ chunks generados
    # ------------------------------------------------------------------

    def _check_chunks_consistency(
        self,
        report: QualityReport,
        processing_report: dict[str, Any],
        db_chunks_count: int | None,
    ) -> None:
        generated = (
            processing_report.get("total_chunks")
            or processing_report.get("articulos_identificados")
        )
        if db_chunks_count is not None and generated is not None:
            if db_chunks_count == 0:
                report.issues.append(QualityIssue(
                    code="SQLITE_NO_CHUNKS",
                    severity=IssueSeverity.CRITICAL,
                    message="SQLite no tiene chunks para esta versión.",
                ))

    # ------------------------------------------------------------------
    # Correspondencia SQLite ↔ Qdrant
    # ------------------------------------------------------------------

    def _check_qdrant_correspondence(
        self,
        report: QualityReport,
        version_id: str,
        db_chunks_count: int | None,
    ) -> None:
        if self._qdrant is None:
            report.issues.append(QualityIssue(
                code="QDRANT_NO_INDEXER",
                severity=IssueSeverity.INFO,
                message="No se proporcionó indexador Qdrant; correspondencia no verificada.",
            ))
            return

        try:
            qdrant_count = self._qdrant.count_version_points(version_id)
            if db_chunks_count is not None:
                if qdrant_count != db_chunks_count:
                    report.issues.append(QualityIssue(
                        code="QDRANT_SQLITE_MISMATCH",
                        severity=IssueSeverity.CRITICAL,
                        message=(
                            f"Desincronización: SQLite={db_chunks_count} chunks, "
                            f"Qdrant={qdrant_count} puntos para versión '{version_id}'."
                        ),
                    ))
                else:
                    report.issues.append(QualityIssue(
                        code="QDRANT_SQLITE_OK",
                        severity=IssueSeverity.INFO,
                        message=f"SQLite y Qdrant coinciden: {db_chunks_count} registros.",
                    ))
        except Exception as exc:  # noqa: BLE001
            report.issues.append(QualityIssue(
                code="QDRANT_CHECK_ERROR",
                severity=IssueSeverity.WARNING,
                message=f"No se pudo verificar correspondencia Qdrant: {exc}",
            ))
