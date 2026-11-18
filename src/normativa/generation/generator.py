"""Generador RAG con modelo local Ollama.

Responsabilidades:
- Construir un prompt seguro con los fragmentos normativos recuperados.
- Llamar al LLM local (qwen2.5:7b por defecto) vía Ollama.
- Diferenciar respuestas completas, evidencia parcial, solicitudes de aclaración y abstenciones reales.
- Extraer y verificar los chunk_ids declarados por el LLM.
- Nunca aceptar IDs que no estén en la lista de chunks recuperados.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field

from llama_index.llms.ollama import Ollama

from normativa.config import settings
from normativa.retrieval.retriever import RetrievedChunk

# ---------------------------------------------------------------------------
# Prompt del sistema — no inyectable por el usuario
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
Eres un asistente informativo del Reglamento de Trabajo de Grado de las \
Unidades Tecnológicas de Santander (UTS).

DIRECTRICES OBLIGATORIAS (no negociables):
1. FUENTE EXCLUSIVA: Responde ÚNICAMENTE basándote en los fragmentos normativos suministrados.
   - NO inventes artículos, plazos, porcentajes, requisitos ni procedimientos no contenidos en los fragmentos.
   - Tus respuestas son estrictamente orientativas para la comunidad académica de las UTS.

2. POLÍTICA DE RESPUESTA, CLARIFICACIÓN Y ABSTENCIÓN:
   a) EVIDENCIA SUFICIENTE: Si los fragmentos contienen la información requerida, responde de forma clara, directa y estructurada, explicando lo que establece el reglamento con sus artículos y parágrafos pertinentes.
   b) EVIDENCIA PARCIAL O CONSULTA AMBIGUA: Si los fragmentos contienen información relevante sobre el tema pero no cubren todos los aspectos o el resultado depende de variables no especificadas (por ejemplo: la modalidad del estudiante o la etapa del trámite):
      - Explica con precisión lo que la norma SÍ establece (condiciones, plazos generales, requisitos o excepciones).
      - Señala con claridad qué aspecto no está detallado en la norma.
      - Solicita amablemente al usuario la aclaración pertinente para su caso (por ejemplo: indicar la modalidad cursada).
      - NUNCA uses «ABSTENCIÓN:» si los fragmentos contienen disposiciones aplicables al tema.
   c) CONSULTA FUERA DE DOMINIO: Si la pregunta NO tiene ninguna relación con el reglamento o los fragmentos no aportan ninguna evidencia aplicable (por ejemplo: temas comerciales, no universitarios, etc.):
      - Responde iniciando EXACTAMENTE con: «ABSTENCIÓN: [motivo claro de abstención...]»

3. CITAS Y DECLARACIÓN DE EVIDENCIA:
   Al final de tu respuesta, debes incluir OBLIGATORIAMENTE una línea con el formato exacto:
   EVIDENCIA_USADA: [chunk_id_1, chunk_id_2, ...]
   Incluye únicamente los IDs de los fragmentos que realmente sirvieron de sustento a la respuesta.

4. ESTILO Y REDACCIÓN:
   - Responde en español claro, profesional y académico.
   - Sintetiza la información de forma estructurada. No repitas pasajes irrelevantes.
"""

_DISCLAIMER = (
    "Esta respuesta es orientativa y se basa en el reglamento indexado. "
    "Para decisiones oficiales, consulte directamente a la Secretaría Académica o al Comité de Trabajo de Grado de la UTS."
)

_EVIDENCE_LINE_RE = re.compile(r"EVIDENCIA_USADA\s*:\s*\[([^\]]*)\]", re.IGNORECASE)
_CLARIFICATION_RE = re.compile(
    r"\b(?:aclaraci[oó]n|ind[ií]canos|especif[ií]qu?e|ind[ií]qu?e|cu[aá]l\s+es\s+tu\s+modalidad|qu[eé]\s+modalidad)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Tipos de retorno
# ---------------------------------------------------------------------------


@dataclass
class GenerationResult:
    answer: str
    abstained: bool
    abstention_reason: str | None
    used_chunk_ids: list[str]  # IDs verificados contra retrieved_chunks
    generation_ms: float
    raw_response: str = field(repr=False, default="")
    response_type: str = "normative"  # "normative", "clarification", "abstention"
    clarification_needed: bool = False
    clarification_question: str | None = None


# ---------------------------------------------------------------------------
# Generador
# ---------------------------------------------------------------------------


class NormativeGenerator:
    """Llama al LLM local y produce respuestas sustentadas en evidencia."""

    def __init__(
        self,
        llm_model: str = settings.LLM_MODEL,
        ollama_base_url: str = settings.OLLAMA_BASE_URL,
        llm=None,  # inyectable para tests
    ) -> None:
        self._llm_model = llm_model
        self._ollama_base_url = ollama_base_url
        self._llm = llm  # si se inyecta, se usa directamente

    def _get_llm(self):
        if self._llm is not None:
            return self._llm
        return Ollama(model=self._llm_model, base_url=self._ollama_base_url, request_timeout=120.0)

    @staticmethod
    def _build_context(chunks: list[RetrievedChunk]) -> str:
        """Construye el contexto documental con etiquetas claras para evitar inyección."""
        lines: list[str] = ["=== FRAGMENTOS NORMATIVOS ==="]
        for chunk in chunks:
            lines.append(f"\n[FRAGMENTO ID={chunk.chunk_id}]")
            lines.append(f"Ubicación: {chunk.location_hint}")
            lines.append(f"Texto:\n{chunk.text}")
            lines.append(f"[/FRAGMENTO ID={chunk.chunk_id}]")
        lines.append("=== FIN FRAGMENTOS NORMATIVOS ===")
        return "\n".join(lines)

    @staticmethod
    def _parse_used_ids(
        raw: str,
        available_ids: set[str],
        chunks: list[RetrievedChunk],
        is_abstained: bool,
    ) -> list[str]:
        """Extrae y verifica los IDs de evidencia declarados por el LLM.

        Si hubo abstención, nunca devuelve citas.
        Si el LLM no incluyó la línea pero respondió fundamentadamente,
        asigna los IDs de los chunks primarios cuyos artículos fueron citados en el texto.
        """
        if is_abstained:
            return []

        match = _EVIDENCE_LINE_RE.search(raw)
        if match:
            raw_ids = [cid.strip().strip("'\"") for cid in match.group(1).split(",") if cid.strip()]
            valid = [cid for cid in raw_ids if cid in available_ids]
            if valid:
                return valid

        # Fallback de seguridad: si el LLM no incluyó EVIDENCIA_USADA o falló el formato,
        # asociar los chunks cuyos artículos son nombrados en la respuesta o los chunks principales
        detected_ids: list[str] = []
        raw_lower = raw.lower()
        for chunk in chunks:
            art_num = chunk.payload.get("articulo_numero")
            if art_num is not None:
                art_pattern = rf"\b(?:art[ií]culo|art\.?)\s*{art_num}\b"
                if re.search(art_pattern, raw_lower):
                    detected_ids.append(chunk.chunk_id)

        if detected_ids:
            return detected_ids

        # Si aún está vacío y hay chunks recuperados relevantes, asociar hasta 3 chunks con mayor score
        sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)
        return [c.chunk_id for c in sorted_chunks[:3]]

    @staticmethod
    def _clean_answer(raw: str) -> str:
        """Elimina la línea EVIDENCIA_USADA de la respuesta final."""
        return _EVIDENCE_LINE_RE.sub("", raw).strip()

    def generate(
        self,
        query: str,
        retrieved_chunks: list[RetrievedChunk],
    ) -> GenerationResult:
        """Genera una respuesta basada en los chunks recuperados.

        Si la lista de chunks está vacía, abstiene sin llamar al LLM.
        """
        t0 = time.perf_counter()

        if not retrieved_chunks:
            return GenerationResult(
                answer="ABSTENCIÓN: No se recuperaron fragmentos normativos relevantes para esta consulta.",
                abstained=True,
                abstention_reason="Sin evidencia suficiente",
                used_chunk_ids=[],
                generation_ms=0.0,
                response_type="abstention",
            )

        context = self._build_context(retrieved_chunks)
        available_ids = {c.chunk_id for c in retrieved_chunks}

        prompt = (
            f"{_SYSTEM_PROMPT}\n\n"
            f"{context}\n\n"
            f"=== PREGUNTA DEL USUARIO ===\n"
            f"{query}\n"
            f"=== FIN PREGUNTA ===\n\n"
            f"Responde ahora siguiendo todas las reglas indicadas:"
        )

        try:
            llm = self._get_llm()
            raw = str(llm.complete(prompt))
        except Exception as exc:
            raise RuntimeError(f"Error al llamar al LLM: {exc}") from exc

        generation_ms = (time.perf_counter() - t0) * 1000

        # Detectar abstención
        abstained = raw.strip().upper().startswith("ABSTENCIÓN:")
        abstention_reason: str | None = None
        response_type = "normative"
        clarification_needed = False
        clarification_question: str | None = None

        if abstained:
            first_line = raw.strip().split("\n")[0]
            abstention_reason = first_line.split(":", 1)[1].strip() if ":" in first_line else "Sin evidencia"
            response_type = "abstention"
        else:
            # Evaluar si la respuesta solicita una aclaración al estudiante
            clean_text = self._clean_answer(raw)
            if _CLARIFICATION_RE.search(clean_text) or "¿cuál es tu modalidad" in clean_text.lower():
                clarification_needed = True
                response_type = "clarification"
                # Extraer posible pregunta de aclaración al final
                lines = [l.strip() for l in clean_text.split("\n") if l.strip()]
                for l in reversed(lines):
                    if "?" in l:
                        clarification_question = l
                        break

        used_ids = self._parse_used_ids(raw, available_ids, retrieved_chunks, abstained)
        clean_answer = self._clean_answer(raw)

        return GenerationResult(
            answer=clean_answer,
            abstained=abstained,
            abstention_reason=abstention_reason,
            used_chunk_ids=used_ids,
            generation_ms=generation_ms,
            raw_response=raw,
            response_type=response_type,
            clarification_needed=clarification_needed,
            clarification_question=clarification_question,
        )
