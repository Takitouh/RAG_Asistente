from __future__ import annotations

import re
from normativa.corpus.models import NormativeChunk
from normativa.ingestion.models import ParsedDocument


def build_chunks_from_parsed_document(
    parsed: ParsedDocument,
    version_id: str,
    document_id: str,
    document_name: str,
    categoria_id: str | None = None,
    family_id: str | None = None,
) -> list[NormativeChunk]:
    chunks: list[NormativeChunk] = []

    # 1. Preámbulo (si existe y tiene contenido sustancial)
    if parsed.preambulo and len(parsed.preambulo.strip()) > 20:
        chunk_id = f"{version_id}_preambulo"
        # El preámbulo del Acuerdo 01-026 (uts_tg_2021) abarca las páginas 1 y 2.
        # Para versiones futuras, page_end se puede extender del mismo modo.
        preamble_page_end = 2 if "uts_tg_2021" in version_id else 1
        preamble_loc_pages = "págs. 1-2" if preamble_page_end == 2 else "pág. 1"
        chunks.append(
            NormativeChunk(
                chunk_id=chunk_id,
                version_id=version_id,
                document_id=document_id,
                document_name=document_name,
                categoria_id=categoria_id,
                family_id=family_id,
                capitulo_numero=None,
                capitulo_romano=None,
                capitulo_titulo=None,
                articulo_numero=None,
                articulo_ordinal=None,
                articulo_tipo="preambulo",
                paragrafo_numero=None,
                inciso_marker=None,
                page_start=1,
                page_end=preamble_page_end,
                texto=f"PREÁMBULO:\n{parsed.preambulo.strip()}",
                ocr_confidence=None,
                location_hint=f"Preámbulo, {document_name} ({preamble_loc_pages})",
            )
        )

    # 2. Artículos y sus subdivisiones
    for art_idx, art in enumerate(parsed.articulos):
        art_ident = str(art.numero) if art.numero is not None else str(art.ordinal or art_idx + 1)
        safe_art_ident = re.sub(r"[^A-Za-z0-9_]", "_", art_ident)

        # Rastrear marcadores ya emitidos para detectar duplicados (anomalías documentales, e.g. Art. 4).
        _used_inciso_markers: dict[str, int] = {}

        context_parts: list[str] = []
        if art.capitulo_numero is not None or art.capitulo_romano:
            cap_id = art.capitulo_romano or str(art.capitulo_numero)
            cap_title = f" - {art.capitulo_titulo}" if art.capitulo_titulo else ""
            context_parts.append(f"Capítulo {cap_id}{cap_title}")

        art_label = f"Artículo {art.numero}" if art.numero is not None else f"Artículo {art.ordinal or ''}".strip()
        if art.kind == "acuerdo":
            art_label = f"{art_label} (Acuerdo)"
        context_parts.append(art_label)

        header_prefix = ". ".join(context_parts)

        # Si el artículo tiene cuerpo de texto principal
        if art.texto.strip():
            chunk_id = f"{version_id}_art_{safe_art_ident}_cuerpo"
            location = f"{', '.join(context_parts)} (págs. {art.page_start}-{art.page_end})"
            chunks.append(
                NormativeChunk(
                    chunk_id=chunk_id,
                    version_id=version_id,
                    document_id=document_id,
                    document_name=document_name,
                    categoria_id=categoria_id,
                    family_id=family_id,
                    capitulo_numero=art.capitulo_numero,
                    capitulo_romano=art.capitulo_romano,
                    capitulo_titulo=art.capitulo_titulo,
                    articulo_numero=art.numero,
                    articulo_ordinal=art.ordinal,
                    articulo_tipo=art.kind,
                    paragrafo_numero=None,
                    inciso_marker=None,
                    page_start=art.page_start,
                    page_end=art.page_end,
                    texto=f"{header_prefix}:\n{art.texto.strip()}",
                    ocr_confidence=art.ocr_confidence_mean,
                    location_hint=location,
                )
            )

        def _resolve_inciso_id(raw_marker: str | None, fallback_idx: int) -> tuple[str, str, str]:
            """Devuelve (chunk_id_sufijo, marker_display, location_hint_sufijo) con dedup _bis."""
            base = str(raw_marker) if raw_marker else str(fallback_idx + 1)
            count = _used_inciso_markers.get(base, 0)
            _used_inciso_markers[base] = count + 1
            if count == 0:
                return f"inc_{base}", base, f"Inciso {base}"
            suffix = "_bis" if count == 1 else f"_ter{count}"
            return f"inc_{base}{suffix}", f"{base} (segundo)", f"Inciso {base} (segundo; anomalía documental original)"

        # Incisos directos del artículo (si no están dentro de un parágrafo)
        for inc_idx, inc in enumerate(art.incisos):
            inc_id_suf, marker_display, loc_suf = _resolve_inciso_id(inc.marker, inc_idx)
            chunk_id = f"{version_id}_art_{safe_art_ident}_{inc_id_suf}"
            location = f"{', '.join(context_parts)}, {loc_suf} (págs. {art.page_start}-{art.page_end})"
            chunks.append(
                NormativeChunk(
                    chunk_id=chunk_id,
                    version_id=version_id,
                    document_id=document_id,
                    document_name=document_name,
                    categoria_id=categoria_id,
                    family_id=family_id,
                    capitulo_numero=art.capitulo_numero,
                    capitulo_romano=art.capitulo_romano,
                    capitulo_titulo=art.capitulo_titulo,
                    articulo_numero=art.numero,
                    articulo_ordinal=art.ordinal,
                    articulo_tipo=art.kind,
                    paragrafo_numero=None,
                    inciso_marker=inc.marker,
                    page_start=art.page_start,
                    page_end=art.page_end,
                    texto=f"{header_prefix}, Inciso {marker_display}):\n{inc.texto.strip()}",
                    ocr_confidence=art.ocr_confidence_mean,
                    location_hint=location,
                )
            )

        # Parágrafos del artículo
        for par_idx, par in enumerate(art.paragrafos):
            par_num_str = par.numero if par.numero is not None else "único"
            par_label = f"Parágrafo {par_num_str}"
            par_content_lines = [par.texto.strip()] if par.texto.strip() else []

            for inc in par.incisos:
                par_content_lines.append(f"  {inc.marker}) {inc.texto.strip()}")

            par_full_text = "\n".join(par_content_lines).strip()
            if not par_full_text:
                continue

            chunk_id = f"{version_id}_art_{safe_art_ident}_par_{par_num_str}"
            location = f"{', '.join(context_parts)}, {par_label} (págs. {art.page_start}-{art.page_end})"
            chunks.append(
                NormativeChunk(
                    chunk_id=chunk_id,
                    version_id=version_id,
                    document_id=document_id,
                    document_name=document_name,
                    categoria_id=categoria_id,
                    family_id=family_id,
                    capitulo_numero=art.capitulo_numero,
                    capitulo_romano=art.capitulo_romano,
                    capitulo_titulo=art.capitulo_titulo,
                    articulo_numero=art.numero,
                    articulo_ordinal=art.ordinal,
                    articulo_tipo=art.kind,
                    paragrafo_numero=par.numero,
                    inciso_marker=None,
                    page_start=art.page_start,
                    page_end=art.page_end,
                    texto=f"{header_prefix}, {par_label}:\n{par_full_text}",
                    ocr_confidence=art.ocr_confidence_mean,
                    location_hint=location,
                )
            )

        # Incisos que no quedaron capturados dentro de parágrafos
        for inc_idx, inc in enumerate(art.incisos):
            pass

    # 3. Cierre (si existe y tiene contenido sustancial)
    if parsed.cierre and len(parsed.cierre.strip()) > 10:
        chunk_id = f"{version_id}_cierre"
        chunks.append(
            NormativeChunk(
                chunk_id=chunk_id,
                version_id=version_id,
                document_id=document_id,
                document_name=document_name,
                categoria_id=categoria_id,
                family_id=family_id,
                capitulo_numero=None,
                capitulo_romano=None,
                capitulo_titulo=None,
                articulo_numero=None,
                articulo_ordinal=None,
                articulo_tipo="cierre",
                paragrafo_numero=None,
                inciso_marker=None,
                page_start=parsed.num_pages,
                page_end=parsed.num_pages,
                texto=f"CIERRE / PUBLICACIÓN:\n{parsed.cierre.strip()}",
                ocr_confidence=None,
                location_hint=f"Cierre, {document_name} (pág. {parsed.num_pages})",
            )
        )

    return chunks
