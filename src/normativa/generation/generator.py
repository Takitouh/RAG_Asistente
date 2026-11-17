"""Generador RAG con modelo local Ollama.

Responsabilidades:
- Construir un prompt seguro con los fragmentos normativos recuperados.
- Llamar al LLM local (qwen2.5:7b por defecto) vía Ollama.
- Detectar abstención («ABSTENCIÓN:» en la respuesta).
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

REGLAS OBLIGATORIAS (no negociables):
1. Responde ÚNICAMENTE con información de los fragmentos normativos proporcionados.
2. NO inventes artículos, plazos, requisitos ni excepciones que no aparezcan en los fragmentos.
3. Si la evidencia es insuficiente o la pregunta está fuera del alcance del reglamento,
   responde comenzando EXACTAMENTE con la palabra «ABSTENCIÓN:» seguida del motivo.
4. Al final de tu respuesta incluye una línea con el siguiente formato exacto:
   EVIDENCIA_USADA: [chunk_id_1, chunk_id_2, ...]
   Incluye solo los IDs de los fragmentos que realmente usaste como fuente.
5. Responde en español claro para estudiantes y docentes.
6. Tus respuestas son orientativas; no constituyen resoluciones ni decisiones oficiales de la UTS.
7. No repitas el texto de los fragmentos de forma literal; sintetiza la información.
"""

_DISCLAIMER = (
    "Esta respuesta es orientativa y se basa en el reglamento indexado. "
    "Para decisiones oficiales, consulte directamente a la Secretaría Académica de la UTS."
)

_EVIDENCE_LINE_RE = re.compile(r"EVIDENCIA_USADA\s*:\s*\[([^\]]*)\]", re.IGNORECASE)


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
    def _parse_used_ids(raw: str, available_ids: set[str]) -> list[str]:
        """Extrae y verifica los IDs de evidencia declarados por el LLM."""
        match = _EVIDENCE_LINE_RE.search(raw)
        if not match:
            return []
        raw_ids = [cid.strip().strip("'\"") for cid in match.group(1).split(",")]
        # Solo se aceptan IDs que realmente están en los chunks recuperados
        return [cid for cid in raw_ids if cid in available_ids]

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
        if abstained:
            # Extraer motivo (texto después de "ABSTENCIÓN:")
            first_line = raw.strip().split("\n")[0]
            abstention_reason = first_line.split(":", 1)[1].strip() if ":" in first_line else "Sin evidencia"

        used_ids = self._parse_used_ids(raw, available_ids)
        clean_answer = self._clean_answer(raw)

        return GenerationResult(
            answer=clean_answer,
            abstained=abstained,
            abstention_reason=abstention_reason,
            used_chunk_ids=used_ids,
            generation_ms=generation_ms,
            raw_response=raw,
        )
