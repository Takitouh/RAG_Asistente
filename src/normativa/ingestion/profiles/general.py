"""src/normativa/ingestion/profiles/general.py

Procesador para el perfil 'documento_general' (Perfil D).
Permite procesar documentos que no se ajusten a los perfiles A, B o C.
Segmentación por encabezados, párrafos y páginas.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from normativa.corpus.models import NormativeChunk
from normativa.ingestion.extractor import PageText
from normativa.ingestion.profiles.base import BaseProfileProcessor, DocumentProfile, ProfileProcessingResult

MAX_CHUNK_CHARS = 2000
MIN_CHUNK_CHARS = 60


class GeneralProfileProcessor(BaseProfileProcessor):
    @property
    def profile(self) -> DocumentProfile:
        return DocumentProfile.DOCUMENTO_GENERAL

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
        anomalies: list[str] = []

        page_texts: list[tuple[int, str]] = []
        for p in pages:
            lines = [ln.text.strip() for ln in p.lines if ln.text.strip()]
            if lines:
                page_texts.append((p.page_number, "\n".join(lines)))

        chunk_idx = 0
        for p_num, p_text in page_texts:
            blocks = re.split(r"\n{2,}|\n(?=[0-9]{1,2}\.\s+[A-ZÁÉÍÓÚÜÑ])", p_text)
            current_buf: list[str] = []
            current_len = 0

            def emit_chunk(buf: list[str], pnum: int) -> None:
                nonlocal chunk_idx
                chunk_text = "\n\n".join(buf)
                if len(chunk_text) >= MIN_CHUNK_CHARS:
                    chunk_idx += 1
                    cid = f"{version_id}_gen_p{pnum}_c{chunk_idx}"
                    chunks.append(
                        NormativeChunk(
                            chunk_id=cid,
                            version_id=version_id,
                            document_id=document_id,
                            document_name=document_name,
                            categoria_id=categoria_id,
                            family_id=family_id,
                            capitulo_numero=pnum,
                            capitulo_romano=str(pnum),
                            capitulo_titulo=f"Página {pnum}",
                            articulo_numero=chunk_idx,
                            articulo_ordinal=None,
                            articulo_tipo="documento_general",
                            paragrafo_numero=None,
                            inciso_marker=None,
                            page_start=pnum,
                            page_end=pnum,
                            texto=f"{document_name} (pág. {pnum}):\n{chunk_text}",
                            ocr_confidence=None,
                            location_hint=f"{document_name}, pág. {pnum}",
                            extra_metadata={"tipo": "documento_general", "pagina": pnum},
                        )
                    )

            for block in blocks:
                block = block.strip()
                if not block:
                    continue
                if current_len + len(block) > MAX_CHUNK_CHARS and current_buf:
                    emit_chunk(current_buf, p_num)
                    current_buf = [block]
                    current_len = len(block)
                else:
                    current_buf.append(block)
                    current_len += len(block)

            if current_buf:
                emit_chunk(current_buf, p_num)

        if not chunks:
            anomalies.append("El documento general no produjo ningún fragmento.")

        report: dict[str, Any] = {
            "profile": self.profile.value,
            "num_pages": len(pages),
            "total_chunks": len(chunks),
            "anomalies": anomalies,
            "statistics": {"paginas": len(pages), "chunks_generados": len(chunks)},
            "categoria_id": categoria_id,
            "family_id": family_id,
        }

        return ProfileProcessingResult(
            profile=self.profile,
            num_pages=len(pages),
            chunks=chunks,
            report=report,
            metadata={},
        )
