"""Proveedores locales de generación estructurada."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx
from pydantic import BaseModel, ValidationError

from normativa.config import Settings


class GenerationError(RuntimeError):
    """Fallo técnico de generación, con mediciones cuando el servidor respondió."""

    def __init__(self, message: str, completion: GenerationCompletion | None = None) -> None:
        super().__init__(message)
        self.completion = completion


class GenerationTimeout(GenerationError):
    """El proveedor agotó su tiempo de espera."""


@dataclass(frozen=True)
class GenerationRequest:
    system: str
    prompt: str
    schema: dict
    context_tokens: int
    output_tokens: int

    def ollama_payload(self, model: str) -> dict:
        return {
            "model": model, "stream": False, "truncate": False, "format": self.schema,
            "messages": [{"role": "system", "content": self.system}, {"role": "user", "content": self.prompt}],
            "options": {"num_ctx": self.context_tokens, "num_predict": self.output_tokens, "temperature": 0},
        }


@dataclass(frozen=True)
class GenerationCompletion:
    text: str
    input_tokens: int
    output_tokens: int
    done_reason: str


class LLMProvider(Protocol):
    @property
    def provider_name(self) -> str: ...
    @property
    def model_name(self) -> str: ...
    def complete(self, request: GenerationRequest) -> str | GenerationCompletion: ...


class _OllamaMessage(BaseModel):
    content: str


class _OllamaResponse(BaseModel):
    message: _OllamaMessage
    done: bool
    done_reason: str
    prompt_eval_count: int
    eval_count: int


class OllamaProvider:
    provider_name = "ollama"

    def __init__(self, model: str, base_url: str, timeout: float) -> None:
        self.model_name = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, request: GenerationRequest) -> GenerationCompletion:
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=request.ollama_payload(self.model_name),
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = _OllamaResponse.model_validate_json(response.content)
        except httpx.TimeoutException as exc:
            raise GenerationTimeout("Ollama agotó el tiempo de espera.") from exc
        except (httpx.HTTPError, ValidationError) as exc:
            raise GenerationError("Ollama no devolvió una respuesta válida.") from exc

        completion = GenerationCompletion(
            result.message.content, result.prompt_eval_count, result.eval_count, result.done_reason,
        )
        if (
            not result.done or result.done_reason != "stop"
            or result.prompt_eval_count > request.context_tokens - request.output_tokens
            or result.eval_count > request.output_tokens
        ):
            raise GenerationError("La generación superó el presupuesto de contexto o quedó incompleta.", completion)
        return completion


class SimulatedLLMProvider:
    """Simulación configurable para pruebas sin servidor generativo."""

    provider_name = "simulated"
    model_name = "simulated"

    def __init__(
        self,
        response: str = (
            '{"status":"insufficient_evidence","answer":"","used_chunk_ids":[],'
            '"abstention_reason":"Sin evidencia suficiente.","unanswered_parts":[]}'
        ),
    ) -> None:
        self.response = response

    def complete(self, request: GenerationRequest) -> str:
        return self.response


def get_llm_provider(config: Settings) -> LLMProvider:
    provider = config.LLM_PROVIDER.strip().lower()
    if provider == "ollama":
        return OllamaProvider(config.LLM_MODEL, config.OLLAMA_BASE_URL, config.LLM_TIMEOUT_SECONDS)
    if provider in {"simulated", "mock"}:
        return SimulatedLLMProvider()
    raise GenerationError(f"Proveedor generativo desconocido: {provider}")
