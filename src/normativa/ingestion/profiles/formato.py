"""src/normativa/ingestion/profiles/formato.py

Procesador especializado para el perfil 'formato_institucional' (ej. F-DC-124 a F-DC-130, F-AM-04, F-DC-196).
Reconoce:
- Código y versión institucional en encabezados.
- Secciones de la plantilla (Datos generales, Objetivos, Metodología, Cronograma, Criterios de evaluación).
- Instrucciones de diligenciamiento vs campos de formulario.
- Criterios de calificación y rejillas de evaluación (ej. F-DC-129).
- Conserva el contexto de la plantilla sin atribuirle rango normativo reglamentario.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from normativa.corpus.models import NormativeChunk
from normativa.ingestion.extractor import PageText
from normativa.ingestion.profiles.base import BaseProfileProcessor, DocumentProfile, ProfileProcessingResult


class FormatoProfileProcessor(BaseProfileProcessor):
    @property
    def profile(self) -> DocumentProfile:
        return DocumentProfile.FORMATO_INSTITUCIONAL

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
        chunks: list[NormativeChunk] = []

        # 1. Detectar código de formato
        codigo_formato = "FORMATO"
        for code_cand in ["F-AM-04", "F-DC-124", "F-DC-125", "F-DC-126", "F-DC-127", "F-DC-128", "F-DC-129", "F-DC-130", "F-DC-196"]:
            if code_cand in document_name or code_cand in str(pdf_path):
                codigo_formato = code_cand
                break

        def _clean_format_line(line: str) -> str:
            """Elimina caracteres de ruptura de palabra generados por LibreOffice/Word."""
            return line.replace("\ufffe", "").replace("\xad", "").strip()

        # 2. Segmentación estructurada por páginas y bloques semánticos
        for p in pages:
            lines = [_clean_format_line(l.text) for l in p.lines if _clean_format_line(l.text)]
            if not lines:
                continue

            p_text = "\n".join(lines)

            # Dividir en bloques lógicos (secciones o párrafos instructivos)
            # Detectar encabezados de sección dentro del formato (ej. "1. INFORMACIÓN GENERAL", "INSTRUCCIONES", "CRITERIOS DE EVALUACIÓN")
            section_splits = re.split(r"\n(?=[0-9]{1,2}\.\s+[A-ZÁÉÍÓÚÜÑ\s]{3,80})", p_text)

            for sec_idx, sec_content in enumerate(section_splits, start=1):
                clean_sec = sec_content.strip()
                if not clean_sec or len(clean_sec) < 15:
                    continue

                first_line = clean_sec.split("\n")[0].strip()
                sec_title = first_line[:60]

                is_instruction = any(
                    w in clean_sec.lower()
                    for w in ["instrucción", "instrucciones", "diligenciar", "nota:", "orientación", "criterio"]
                )
                chunk_type = "formato_instruccion" if is_instruction else "formato_seccion"

                cid = f"{version_id}_p{p.page_number}_s{sec_idx}"
                loc = f"{codigo_formato}, Pág. {p.page_number} ({sec_title})"

                header = f"{codigo_formato} (Plantilla institucional de trabajo de grado) - {sec_title}:\n"
                full_chunk_text = f"{header}{clean_sec}"

                chunks.append(
                    NormativeChunk(
                        chunk_id=cid,
                        version_id=version_id,
                        document_id=document_id,
                        document_name=document_name,
                        categoria_id=categoria_id,
                        family_id=family_id,
                        capitulo_numero=p.page_number,
                        capitulo_romano=str(p.page_number),
                        capitulo_titulo=f"Página {p.page_number}",
                        articulo_numero=sec_idx,
                        articulo_ordinal=None,
                        articulo_tipo=chunk_type,
                        paragrafo_numero=None,
                        inciso_marker=None,
                        page_start=p.page_number,
                        page_end=p.page_number,
                        texto=full_chunk_text,
                        ocr_confidence=p.ocr_confidence,
                        location_hint=loc,
                        extra_metadata={
                            "codigo_formato": codigo_formato,
                            "tipo": chunk_type,
                            "es_instruccion": is_instruction,
                        },
                    )
                )

        report = {
            "profile": self.profile.value,
            "num_pages": len(pages),
            "codigo_formato": codigo_formato,
            "total_chunks": len(chunks),
            "anomalies": [],
            "statistics": {
                "paginas": len(pages),
                "chunks_generados": len(chunks),
            },
            "categoria_id": categoria_id,
            "family_id": family_id,
        }

        metadata = {
            "codigo_formato": codigo_formato,
        }

        return ProfileProcessingResult(
            profile=self.profile,
            num_pages=len(pages),
            chunks=chunks,
            report=report,
            metadata=metadata,
        )
