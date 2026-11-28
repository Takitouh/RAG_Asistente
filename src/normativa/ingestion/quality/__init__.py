"""src/normativa/ingestion/quality/__init__.py

Módulo de controles de calidad documental previos a la activación.
"""
from normativa.ingestion.quality.checker import QualityChecker, QualityReport, QualityIssue, IssueSeverity

__all__ = ["QualityChecker", "QualityReport", "QualityIssue", "IssueSeverity"]
