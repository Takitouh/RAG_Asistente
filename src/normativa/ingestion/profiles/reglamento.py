"""src/normativa/ingestion/profiles/reglamento.py

Procesador especializado para el perfil 'reglamento_estructurado'.
Reconoce: Capítulos, Artículos, Parágrafos, Literales/Incisos, Preámbulo y Cierre.
Preserva el contexto del capítulo y artículo en cada subdivisión y garantiza
continuidad en disposiciones que se extienden a través de páginas.
"""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from normativa.corpus.chunker import build_chunks_from_parsed_document
from normativa.corpus.models import NormativeChunk
from normativa.ingestion.cleaner import clean_pages
from normativa.ingestion.extractor import PageText
from normativa.ingestion.parser import parse_document
from normativa.ingestion.profiles.base import BaseProfileProcessor, DocumentProfile, ProfileProcessingResult


class ReglamentoProfileProcessor(BaseProfileProcessor):
    @property
    def profile(self) -> DocumentProfile:
        return DocumentProfile.REGLAMENTO_ESTRUCTURADO

    def process(
        self,
        pdf_path: Path,
        pages: list[PageText],
        version_id: str,
        document_id: str,
        document_name: str,
        categoria_id: str | None = None,
        family_id: str | None = None,
        expected_articles_count: int | None = None,
    ) -> ProfileProcessingResult:
        # 1. Limpieza de encabezados/pies repetitivos
        clean_pages_result, cleaning_log = clean_pages(pages)

        # 2. Parseo estructural de reglamento
        parsed = parse_document(clean_pages_result, source_file=str(pdf_path))

        # 3. Generación de chunks preservando contexto completo
        chunks = build_chunks_from_parsed_document(
            parsed=parsed,
            version_id=version_id,
            document_id=document_id,
            document_name=document_name,
            categoria_id=categoria_id,
            family_id=family_id,
        )

        # 4. Construcción de matriz de artículos para verificación
        matriz_articulos: list[dict[str, Any]] = []
        for art in parsed.articulos:
            par_list = [p.numero or "único" for p in art.paragrafos]
            inc_list = [i.marker for i in art.incisos] + [
                f"par_{p.numero or 'u'}_{i.marker}" for p in art.paragrafos for i in p.incisos
            ]
            ext_methods = {
                pages[p_idx - 1].method
                for p_idx in range(art.page_start, art.page_end + 1)
                if 1 <= p_idx <= len(pages)
            }
            method_str = "/".join(sorted(ext_methods)) if ext_methods else "text_layer"

            matriz_articulos.append(
                {
                    "numero": art.numero,
                    "kind": art.kind,
                    "ordinal": art.ordinal,
                    "capitulo_numero": art.capitulo_numero,
                    "capitulo_romano": art.capitulo_romano,
                    "capitulo_titulo": art.capitulo_titulo,
                    "page_start": art.page_start,
                    "page_end": art.page_end,
                    "paragrafos_count": len(art.paragrafos),
                    "paragrafos": par_list,
                    "incisos_count": len(inc_list),
                    "incisos": inc_list,
                    "metodo_extraccion": method_str,
                    "confianza_ocr_media": art.ocr_confidence_mean,
                    "flags": art.flags,
                    "estado_comprobacion": "VERIFICADO" if not art.flags else "CON_ADVERTENCIAS",
                    "estado_revision_humana": "PENDIENTE_REVISION_HUMANA",
                }
            )

        numeric_articles = [a["numero"] for a in matriz_articulos if a["numero"] is not None and a["kind"] == "reglamento"]
        total_reglamento_articles = len(numeric_articles)

        anomalies = list(parsed.report.anomalies)

        # Validación contra expected_articles_count si fue configurado
        if expected_articles_count is not None and total_reglamento_articles != expected_articles_count:
            anomalies.append(
                f"Cantidad de artículos ({total_reglamento_articles}) no coincide con el valor esperado ({expected_articles_count})."
            )

        report: dict[str, Any] = {
            "profile": self.profile.value,
            "num_pages": len(pages),
            "extraction_methods": {
                "text_layer": sum(1 for p in pages if p.method == "text_layer"),
                "ocr": sum(1 for p in pages if p.method == "ocr"),
            },
            "articulos_identificados": len(parsed.articulos),
            "articulos_reglamento_count": total_reglamento_articles,
            "expected_articles_count": expected_articles_count,
            "min_articulo": min(numeric_articles) if numeric_articles else None,
            "max_articulo": max(numeric_articles) if numeric_articles else None,
            "articulos_faltantes": sorted(
                set(range(1, (max(numeric_articles) if numeric_articles else 0) + 1)) - set(numeric_articles)
            ),
            "anomalies": anomalies,
            "repairs": [asdict(r) for r in parsed.report.repairs],
            "statistics": parsed.report.statistics,
            "cleaning_statistics": cleaning_log.statistics,
            "categoria_id": categoria_id,
            "family_id": family_id,
        }

        metadata = {
            "matriz_articulos": matriz_articulos,
            "preambulo_length": len(parsed.preambulo),
            "cierre_length": len(parsed.cierre),
        }

        return ProfileProcessingResult(
            profile=self.profile,
            num_pages=len(pages),
            chunks=chunks,
            report=report,
            metadata=metadata,
        )
