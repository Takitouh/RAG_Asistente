"""src/normativa/ingestion/profiles/procedimiento.py

Procesador especializado para el perfil 'procedimiento_institucional' (ej. P-DC-28, P-DC-29).
Reconoce:
- Numerales generales (1–6, 8, 9).
- Sección 7: subnumerales 7.1, 7.2, 7.3 y tablas de actividades.
  - Cada actividad registra el subnumeral al que pertenece mediante bounding-box.
  - Se genera un chunk por actividad con metadata de subnumeral y modalidad.
  - El chunk introductorio del numeral 7 es un resumen estructurado (no volcado de tabla).
- Numeral 3 (Definiciones): segmentado en partes ≤1 500 caracteres por definición.
- El OCR condicional (extractor.py) se conserva; este módulo sólo usa pdfplumber para tablas.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pdfplumber

from normativa.corpus.models import NormativeChunk
from normativa.ingestion.extractor import PageText
from normativa.ingestion.profiles.base import BaseProfileProcessor, DocumentProfile, ProfileProcessingResult

# Patrón de subnumeral 7.x
_SUBNUM_RE = re.compile(r"^\s*(7\.[1-9])\.\s*(.*)", re.IGNORECASE)
# Encabezados de sección numérica del procedimiento
_SECTION_RE = re.compile(r"^\s*([1-9])\.\s+([A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑa-záéíóúüñ\s/,]{2,80})$")
# Ruido de encabezado institucional repetido
_HEADER_NOISE_RE = re.compile(
    r"^(PÁGINA\s+\d+|P-DC-\d+\s+VERSIÓN|DOCENCIA|ELABORADO\s+POR|REVISADO\s+POR|APROBADO\s+POR)", re.IGNORECASE
)


def _strip_noise_lines(lines: list[str]) -> list[str]:
    """Elimina líneas de encabezado institucional repetido."""
    return [l for l in lines if not _HEADER_NOISE_RE.match(l.strip())]


class ProcedimientoProfileProcessor(BaseProfileProcessor):
    @property
    def profile(self) -> DocumentProfile:
        return DocumentProfile.PROCEDIMIENTO_INSTITUCIONAL

    def _extract_activities_with_subnumeral(
        self,
        pdf_path: Path,
    ) -> list[dict[str, Any]]:
        """Extrae actividades de las tablas asociando cada fila al subnumeral correcto.

        Usa las coordenadas verticales (top) y de página de los encabezados 7.x
        para decidir a qué subnumeral pertenece cada fila, garantizando títulos
        completos multilínea con todas sus modalidades.
        """
        activities: list[dict[str, Any]] = []

        all_subnum_headings: list[tuple[int, float, str, str]] = []  # (page_num, top, subnum, full_title)

        with pdfplumber.open(pdf_path) as plum:
            for p_num, page in enumerate(plum.pages, start=1):
                page_lines = page.extract_text_lines()
                for l_idx, line_obj in enumerate(page_lines):
                    t = line_obj["text"].strip()
                    m = _SUBNUM_RE.match(t)
                    if m:
                        sn = m.group(1)
                        first_part = m.group(2).strip()
                        title_parts = [first_part] if first_part else []
                        for next_l in page_lines[l_idx + 1 : l_idx + 5]:
                            nt = next_l["text"].strip()
                            if (
                                not nt
                                or nt.startswith("No.")
                                or nt.startswith("Actividad")
                                or nt.startswith("ACTIVIDAD")
                                or _SUBNUM_RE.match(nt)
                                or re.match(r"^[1-9]\.", nt)
                            ):
                                break
                            title_parts.append(nt)
                        full_title = " ".join(title_parts).strip()
                        full_title = re.sub(r"[\s:;]+$", "", full_title)
                        full_title = re.sub(r";\s*y\s+se\s+establece.*$", "", full_title, flags=re.IGNORECASE)
                        full_title = re.sub(r"^(?:7\.[1-9]\.?\s*)+", "", full_title).strip()
                        all_subnum_headings.append((p_num, float(line_obj["top"]), sn, full_title))

            current_subnum = "7.1"
            current_subnum_title = ""
            init_71 = [h for h in all_subnum_headings if h[2] == "7.1"]
            if init_71:
                current_subnum_title = init_71[0][3]

            for p_num, page in enumerate(plum.pages, start=1):
                found_tables = page.find_tables()
                for tbl in found_tables:
                    t_top = float(tbl.bbox[1])
                    for sn_page, sn_top, sn, sn_title in all_subnum_headings:
                        if sn_page < p_num or (sn_page == p_num and sn_top <= t_top):
                            current_subnum = sn
                            current_subnum_title = sn_title

                    table_data = tbl.extract()
                    for row in table_data:
                        clean_cells = [
                            str(c).strip().replace("\r", "").replace("\n", " ")
                            for c in row
                            if c is not None and str(c).strip()
                        ]
                        if not clean_cells:
                            continue

                        num_act: int | None = None
                        act_name = ""
                        act_desc = ""
                        act_resp = ""
                        act_reg = ""

                        if clean_cells[0].isdigit() and 1 <= int(clean_cells[0]) <= 30:
                            num_act = int(clean_cells[0])
                            remaining = clean_cells[1:]
                        elif len(clean_cells) > 1 and clean_cells[1].isdigit() and 1 <= int(clean_cells[1]) <= 30:
                            num_act = int(clean_cells[1])
                            remaining = clean_cells[2:]
                        else:
                            continue

                        if len(remaining) >= 4:
                            act_name = remaining[0]
                            act_desc = remaining[1]
                            act_resp = remaining[2]
                            act_reg = remaining[3]
                        elif len(remaining) == 3:
                            act_name = remaining[0]
                            act_desc = remaining[1]
                            act_resp = remaining[2]
                        elif len(remaining) == 2:
                            act_name = remaining[0]
                            act_desc = remaining[1]
                        elif len(remaining) == 1:
                            act_desc = remaining[0]

                        if num_act is not None and (len(act_desc) > 8 or len(act_name) > 4):
                            activities.append(
                                {
                                    "subnumeral": current_subnum,
                                    "subnumeral_titulo": current_subnum_title,
                                    "numero": num_act,
                                    "nombre": act_name.strip(),
                                    "descripcion": act_desc.strip(),
                                    "responsable": act_resp.strip(),
                                    "registro": act_reg.strip(),
                                    "pagina": p_num,
                                }
                            )

        return activities

    def _split_definitions_section(self, sec_body: str, version_id: str, sec: dict) -> list[NormativeChunk]:
        """Divide el texto de Definiciones en chunks semánticamente coherentes ≤1 500 chars."""
        # Intentar dividir por definición (bullet o término seguido de ':')
        raw_blocks = re.split(r"\n(?=[•\-\*]\s+|(?:[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñA-ZÁÉÍÓÚÜÑ\s]{3,40}):)", sec_body)
        parts: list[str] = []
        current_part: list[str] = []
        current_len = 0
        max_len = 1500

        for block in raw_blocks:
            block = block.strip()
            if not block:
                continue
            if current_len + len(block) > max_len and current_part:
                parts.append("\n\n".join(current_part))
                current_part = []
                current_len = 0
            current_part.append(block)
            current_len += len(block)

        if current_part:
            parts.append("\n\n".join(current_part))

        chunks: list[NormativeChunk] = []
        num = sec["numeral"]
        titulo = sec["titulo"]

        for idx, part in enumerate(parts, start=1):
            cid = f"{version_id}_numeral_{num}_p{idx}"
            loc = f"{sec['document_name']}, Numeral {num}: {titulo} (Parte {idx}) (págs. {sec['page_start']}-{sec['page_end']})"
            body = f"{sec['document_name']} - Numeral {num}. {titulo} (Parte {idx}):\n{part}"
            chunks.append(
                NormativeChunk(
                    chunk_id=cid,
                    version_id=version_id,
                    document_id=sec["document_id"],
                    document_name=sec["document_name"],
                    categoria_id=sec["categoria_id"],
                    family_id=sec["family_id"],
                    capitulo_numero=num,
                    capitulo_romano=str(num),
                    capitulo_titulo=titulo,
                    articulo_numero=num,
                    articulo_ordinal=None,
                    articulo_tipo="seccion_procedimiento",
                    paragrafo_numero=None,
                    inciso_marker=None,
                    page_start=sec["page_start"],
                    page_end=sec["page_end"],
                    texto=body,
                    ocr_confidence=None,
                    location_hint=loc,
                    extra_metadata={"numeral": str(num), "tipo": "procedimiento_seccion_definiciones", "parte": idx},
                )
            )
        return chunks

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

        # 1. Extraer actividades con subnumeral
        raw_activities = self._extract_activities_with_subnumeral(pdf_path)

        # 2. Texto por página (limpiando ruido de encabezados)
        full_text_by_page: list[tuple[int, str]] = []
        for p in pages:
            lines = _strip_noise_lines([l.text.strip() for l in p.lines if l.text.strip()])
            full_text_by_page.append((p.page_number, "\n".join(lines)))

        # 3. Parsear secciones numéricas (1–9)
        sections: list[dict[str, Any]] = []
        current_sec: dict[str, Any] | None = None

        # Mapa de keywords canónicas por numeral (1–9). Un match DEBE tener al menos una keyword.
        # Esto evita que registros de tabla (ej. "1. Liquidación de la..." en pág. 9)
        # sobrescriban los numerales auténticos identificados en la página correcta.
        SECTION_CANONICAL: dict[int, list[str]] = {
            1:  ["OBJETIVO", "OBJETO"],
            2:  ["ALCANCE"],
            3:  ["DEFINICIONES Y/O ABREVIATURAS", "DEFINICIONES Y ABREVIATURAS", "DEFINICIONES"],
            4:  ["RESPONSABLE", "RESPONSABLES"],
            5:  ["GENERALIDADES"],
            6:  ["DOCUMENTOS DE REFERENCIA", "POLÍTICAS DE OPERACIÓN", "POLITICAS DE OPERACION"],
            7:  ["DESARROLLO Y/O DESCRIPCIÓN", "DESARROLLO Y DESCRIPCIÓN", "DESCRIPCIÓN DE LAS ACTIVIDADES",
                 "DESARROLLO"],
            8:  ["CONTROLES OPERACIONALES", "CONTROL DE REGISTROS"],
            9:  ["ANEXOS", "CONTROL DE CAMBIOS"],
        }

        def _match_section(line: str, next_expected: int) -> tuple[int, str] | None:
            """Retorna (num, título) solo si:
              - La línea coincide con _SECTION_RE,
              - sec_num >= next_expected (secuencia ascendente estricta),
              - El título contiene al menos una keyword canónica del numeral.
            Nunca acepta el numeral 10 (HISTORIAL DE CAMBIOS, tabla administrativa).
            """
            m = _SECTION_RE.match(line)
            if not m:
                return None
            sec_num = int(m.group(1))
            sec_title = m.group(2).strip()
            # Ignorar numeral 10 (Historial de Cambios, sin relevancia normativa)
            if sec_num == 10:
                return None
            # Secuencia ascendente: no retroceder ni repetir
            if sec_num < next_expected:
                return None
            # Validar keyword canónica obligatoria
            keywords = SECTION_CANONICAL.get(sec_num, [])
            if keywords and not any(kw.lower() in sec_title.lower() for kw in keywords):
                return None
            return sec_num, sec_title

        next_expected_sec = 1  # siguiente numeral esperado (secuencia 1→9)

        for p_num, p_text in full_text_by_page:
            for line in p_text.split("\n"):
                matched = _match_section(line, next_expected_sec)
                if matched:
                    if current_sec:
                        sections.append(current_sec)
                    current_sec = {
                        "numeral": matched[0],
                        "titulo": matched[1],
                        "lines": [],
                        "page_start": p_num,
                        "page_end": p_num,
                        "document_name": document_name,
                        "document_id": document_id,
                        "categoria_id": categoria_id,
                        "family_id": family_id,
                    }
                    next_expected_sec = matched[0] + 1
                elif current_sec:
                    current_sec["lines"].append(line)
                    current_sec["page_end"] = p_num

        if current_sec:
            sections.append(current_sec)

        # 4. Construir chunks de texto (numerales no-7)
        for sec in sections:
            num = sec["numeral"]

            if num == 7:
                # El intro del numeral 7 es un resumen estructurado de subnumerales,
                # NO un volcado de texto de tabla.
                subnums_en_pdf = sorted(
                    {a["subnumeral"] for a in raw_activities},
                    key=lambda s: [int(x) for x in s.split(".")],
                )
                summary_lines = [
                    f"{document_name} - Numeral 7. {sec['titulo']}:",
                    f"Este numeral contiene {len(raw_activities)} actividades distribuidas en {len(subnums_en_pdf)} subnumeral(es):",
                ]
                for sn in subnums_en_pdf:
                    sn_acts = [a for a in raw_activities if a["subnumeral"] == sn]
                    sn_title = sn_acts[0]["subnumeral_titulo"] if sn_acts else sn
                    summary_lines.append(f"  - {sn}. {sn_title}: {len(sn_acts)} actividad(es)")

                cid = f"{version_id}_numeral_7_intro"
                loc = f"{document_name}, Numeral 7: {sec['titulo']} (pág. {sec['page_start']}-{sec['page_end']})"
                chunks.append(
                    NormativeChunk(
                        chunk_id=cid,
                        version_id=version_id,
                        document_id=document_id,
                        document_name=document_name,
                        categoria_id=categoria_id,
                        family_id=family_id,
                        capitulo_numero=7,
                        capitulo_romano="VII",
                        capitulo_titulo=sec["titulo"],
                        articulo_numero=7,
                        articulo_ordinal=None,
                        articulo_tipo="seccion_procedimiento",
                        paragrafo_numero=None,
                        inciso_marker=None,
                        page_start=sec["page_start"],
                        page_end=sec["page_end"],
                        texto="\n".join(summary_lines),
                        ocr_confidence=None,
                        location_hint=loc,
                        extra_metadata={"numeral": "7", "tipo": "procedimiento_seccion_intro"},
                    )
                )
                continue

            sec_body = "\n".join(sec["lines"]).strip()
            if not sec_body:
                continue

            # Numeral 3 (Definiciones): dividir en partes semánticas
            if num == 3:
                def_chunks = self._split_definitions_section(sec_body, version_id, sec)
                chunks.extend(def_chunks)
                continue

            # Secciones cortas o medianas: un chunk si ≤1 800 chars; en caso contrario dividir.
            max_len = 1800
            if len(sec_body) <= max_len:
                cid = f"{version_id}_numeral_{num}"
                loc = f"{document_name}, Numeral {num}: {sec['titulo']} (págs. {sec['page_start']}-{sec['page_end']})"
                chunks.append(
                    NormativeChunk(
                        chunk_id=cid,
                        version_id=version_id,
                        document_id=document_id,
                        document_name=document_name,
                        categoria_id=categoria_id,
                        family_id=family_id,
                        capitulo_numero=num,
                        capitulo_romano=str(num),
                        capitulo_titulo=sec["titulo"],
                        articulo_numero=num,
                        articulo_ordinal=None,
                        articulo_tipo="seccion_procedimiento",
                        paragrafo_numero=None,
                        inciso_marker=None,
                        page_start=sec["page_start"],
                        page_end=sec["page_end"],
                        texto=f"{document_name} - Numeral {num}. {sec['titulo']}:\n{sec_body}",
                        ocr_confidence=None,
                        location_hint=loc,
                        extra_metadata={"numeral": str(num), "tipo": "procedimiento_seccion"},
                    )
                )
            else:
                paragraphs = [p.strip() for p in sec_body.split("\n\n") if p.strip()]
                current_part: list[str] = []
                part_idx = 1
                for par in paragraphs:
                    current_part.append(par)
                    part_str = "\n\n".join(current_part)
                    if len(part_str) >= 1200:
                        cid = f"{version_id}_numeral_{num}_p{part_idx}"
                        loc = f"{document_name}, Numeral {num}: {sec['titulo']} (Parte {part_idx}) (págs. {sec['page_start']}-{sec['page_end']})"
                        chunks.append(
                            NormativeChunk(
                                chunk_id=cid,
                                version_id=version_id,
                                document_id=document_id,
                                document_name=document_name,
                                categoria_id=categoria_id,
                                family_id=family_id,
                                capitulo_numero=num,
                                capitulo_romano=str(num),
                                capitulo_titulo=sec["titulo"],
                                articulo_numero=num,
                                articulo_ordinal=None,
                                articulo_tipo="seccion_procedimiento",
                                paragrafo_numero=None,
                                inciso_marker=None,
                                page_start=sec["page_start"],
                                page_end=sec["page_end"],
                                texto=f"{document_name} - Numeral {num}. {sec['titulo']} (Parte {part_idx}):\n{part_str}",
                                ocr_confidence=None,
                                location_hint=loc,
                                extra_metadata={"numeral": str(num), "tipo": "procedimiento_seccion"},
                            )
                        )
                        current_part = []
                        part_idx += 1
                if current_part:
                    part_str = "\n\n".join(current_part)
                    cid = f"{version_id}_numeral_{num}_p{part_idx}"
                    loc = f"{document_name}, Numeral {num}: {sec['titulo']} (Parte {part_idx}) (págs. {sec['page_start']}-{sec['page_end']})"
                    chunks.append(
                        NormativeChunk(
                            chunk_id=cid,
                            version_id=version_id,
                            document_id=document_id,
                            document_name=document_name,
                            categoria_id=categoria_id,
                            family_id=family_id,
                            capitulo_numero=num,
                            capitulo_romano=str(num),
                            capitulo_titulo=sec["titulo"],
                            articulo_numero=num,
                            articulo_ordinal=None,
                            articulo_tipo="seccion_procedimiento",
                            paragrafo_numero=None,
                            inciso_marker=None,
                            page_start=sec["page_start"],
                            page_end=sec["page_end"],
                            texto=f"{document_name} - Numeral {num}. {sec['titulo']} (Parte {part_idx}):\n{part_str}",
                            ocr_confidence=None,
                            location_hint=loc,
                            extra_metadata={"numeral": str(num), "tipo": "procedimiento_seccion"},
                        )
                    )

        # 5. Un chunk por actividad, con subnumeral en metadata y texto contextualizado
        for act_idx, act in enumerate(raw_activities):
            num_a = act["numero"]
            sn = act["subnumeral"]
            sn_title = act["subnumeral_titulo"]
            name_a = act["nombre"]
            desc_a = act["descripcion"]
            resp_a = act["responsable"]
            reg_a = act["registro"]
            p_a = act["pagina"]

            # ID incluye subnumeral para evitar colisiones entre modalidades
            cid = f"{version_id}_subnum_{sn.replace('.', '_')}_act_{num_a}"
            loc = f"{document_name}, {sn} Actividad {num_a}" + (f" - {name_a}" if name_a else "") + f" (pág. {p_a})"

            body = (
                f"{document_name} - {sn}. {sn_title}: Actividad {num_a}. {name_a}\n"
                f"- Descripción: {desc_a}\n"
                f"- Responsable: {resp_a}\n"
                f"- Registro: {reg_a}"
            )

            chunks.append(
                NormativeChunk(
                    chunk_id=cid,
                    version_id=version_id,
                    document_id=document_id,
                    document_name=document_name,
                    categoria_id=categoria_id,
                    family_id=family_id,
                    capitulo_numero=7,
                    capitulo_romano="VII",
                    capitulo_titulo="DESCRIPCIÓN DE LAS ACTIVIDADES",
                    articulo_numero=num_a,
                    articulo_ordinal=None,
                    articulo_tipo="actividad_procedimiento",
                    paragrafo_numero=None,
                    inciso_marker=None,
                    page_start=p_a,
                    page_end=p_a,
                    texto=body,
                    ocr_confidence=None,
                    location_hint=loc,
                    extra_metadata={
                        "numeral": "7",
                        "subnumeral": sn,
                        "subnumeral_titulo": sn_title,
                        "actividad_numero": num_a,
                        "actividad_nombre": name_a,
                        "responsable": resp_a,
                        "registro": reg_a,
                        "tipo": "actividad",
                    },
                )
            )

        report = {
            "profile": self.profile.value,
            "num_pages": len(pages),
            "secciones_identificadas": [s["numeral"] for s in sections],
            "actividades_identificadas": len(raw_activities),
            "subnumerales": {
                sn: sum(1 for a in raw_activities if a["subnumeral"] == sn)
                for sn in sorted({a["subnumeral"] for a in raw_activities})
            },
            "total_chunks": len(chunks),
            "anomalies": [],
            "statistics": {
                "num_secciones": len(sections),
                "num_actividades": len(raw_activities),
                "chunks_generados": len(chunks),
            },
            "categoria_id": categoria_id,
            "family_id": family_id,
        }

        metadata = {
            "actividades": raw_activities,
            "secciones": [{"numeral": s["numeral"], "titulo": s["titulo"]} for s in sections],
            "subnumerales": report["subnumerales"],
        }

        return ProfileProcessingResult(
            profile=self.profile,
            num_pages=len(pages),
            chunks=chunks,
            report=report,
            metadata=metadata,
        )

