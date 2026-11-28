"""Estimación local con el vocabulario Qwen2 y un respaldo conservador."""
from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

import httpx

from normativa.config import Settings

# Pretokenización Qwen2. Los números se separan de a un dígito.
_QWEN2_PATTERN = (
    r"(?i:'s|'t|'re|'ve|'m|'ll|'d)|[^\r\n\p{L}\p{N}]?\p{L}+|\p{N}|"
    r" ?[^\s\p{L}\p{N}]+[\r\n]*|\s*[\r\n]+|\s+(?!\S)|\s+"
)


def _byte_decoder() -> dict[str, int]:
    # Alfabeto reversible de bytes del vocabulario BPE GPT-2 usado por Qwen2.
    visible = [*range(33, 127), *range(161, 173), *range(174, 256)]
    remaining = [value for value in range(256) if value not in visible]
    return {chr(codepoint): byte for codepoint, byte in zip(
        [*visible, *range(256, 256 + len(remaining))], [*visible, *remaining], strict=True,
    )}


def _qwen_counter(info: dict) -> Callable[[str], int]:
    # tiktoken ya está instalado con LlamaIndex. No se descarga un encoding.
    import tiktoken

    if info.get("tokenizer.ggml.pre") != "qwen2" or info.get("tokenizer.ggml.model") != "gpt2":
        raise ValueError("El modelo local no declara el tokenizador BPE de Qwen2.")
    tokens = info["tokenizer.ggml.tokens"]
    merges = info["tokenizer.ggml.merges"]
    decoder = _byte_decoder()
    # El rango BPE es el orden de las fusiones, tras los 256 tokens de byte.
    ranks = {bytes([byte]): rank for rank, byte in enumerate(decoder.values())}
    for rank, merge in enumerate(merges, start=256):
        pair = merge.split(" ")
        if len(pair) != 2:
            raise ValueError("Fusión BPE no reconocida.")
        ranks[bytes(decoder[character] for character in "".join(pair))] = rank
    if len(ranks) != 256 + len(merges) or set(ranks) != {
        bytes(decoder[character] for character in token) for token in tokens[:len(ranks)]
    }:
        raise ValueError("El vocabulario y las fusiones no son coherentes.")
    encoding = tiktoken.Encoding("ollama-qwen2", pat_str=_QWEN2_PATTERN, mergeable_ranks=ranks, special_tokens={})
    return lambda value: len(encoding.encode_ordinary(value))


@lru_cache(maxsize=4)
def _local_counter(base_url: str, model: str) -> Callable[[str], int] | None:
    try:
        response = httpx.post(f"{base_url.rstrip('/')}/api/show", json={"model": model, "verbose": True}, timeout=4)
        response.raise_for_status()
        return _qwen_counter(response.json()["model_info"])
    except (httpx.HTTPError, ValueError, KeyError, TypeError, ImportError):
        return None


def token_counter(config: Settings, provider_name: str) -> tuple[str, Callable[[str], int]]:
    if config.RAG_TOKEN_ESTIMATION == "qwen2" and provider_name == "ollama":
        counter = _local_counter(config.OLLAMA_BASE_URL, config.LLM_MODEL)
        if counter is not None:
            return "qwen2_bpe", counter
    return "utf8_upper_bound", lambda value: len(value.encode("utf-8"))
