from __future__ import annotations

import time

import psutil
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.llms.ollama import Ollama
from qdrant_client import QdrantClient

from normativa.config import Settings
from normativa.ollama_utils import find_missing_ollama_models


TEXT = "plazo de ejecución del trabajo de grado"
PROMPT = "Responde únicamente con la palabra OK"


def _status(ok: bool) -> str:
    return "OK" if ok else "FALLO"


def _print_result(index: int, message: str, ok: bool) -> None:
    print(f"{_status(ok)} {index}. {message}")


def _model_names(listing: object) -> set[str]:
    models = []
    if isinstance(listing, dict):
        models = listing.get("models", [])
    else:
        models = getattr(listing, "models", [])

    names: set[str] = set()
    for model in models:
        if isinstance(model, dict):
            name = model.get("name") or model.get("model")
        else:
            name = getattr(model, "name", None) or getattr(model, "model", None)
        if name:
            names.add(name)
    return names


def _unwrap_client(wrapper: object) -> object:
    client = getattr(wrapper, "client", None)
    if client is not None:
        return client
    client = getattr(wrapper, "_client", None)
    if client is not None:
        return client
    raise AttributeError("No se encontró cliente Ollama en el wrapper")


def main() -> int:
    settings = Settings()
    total_checks = 0
    passed_checks = 0

    total_checks += 1
    try:
        memory = psutil.virtual_memory()
        cpus = psutil.cpu_count(logical=True)
        _print_result(
            1,
            f"RAM total={memory.total / 1024**3:.2f} GiB, disponible={memory.available / 1024**3:.2f} GiB, CPUs={cpus}",
            True,
        )
        passed_checks += 1
    except Exception as exc:  # noqa: BLE001
        _print_result(1, f"RAM/CPU: {exc}", False)

    total_checks += 1
    try:
        qdrant = QdrantClient(url=settings.QDRANT_URL)
        collections = qdrant.get_collections().collections
        names = []
        for collection in collections:
            if isinstance(collection, dict):
                names.append(collection.get("name", ""))
            else:
                names.append(getattr(collection, "name", ""))
        _print_result(2, f"Qdrant conectado en {settings.QDRANT_URL}; colecciones={names}", True)
        passed_checks += 1
    except Exception as exc:  # noqa: BLE001
        _print_result(2, f"Qdrant: {exc}", False)

    total_checks += 1
    llm = Ollama(model=settings.LLM_MODEL, base_url=settings.OLLAMA_BASE_URL)
    embed_model = OllamaEmbedding(model_name=settings.EMBED_MODEL, base_url=settings.OLLAMA_BASE_URL)
    try:
        client = _unwrap_client(llm)
        listing = client.list()
        names = _model_names(listing)
        missing = find_missing_ollama_models([settings.LLM_MODEL, settings.EMBED_MODEL], names)
        if missing:
            pulls = ", ".join(f"ollama pull {model}" for model in missing)
            _print_result(3, f"Ollama conectado en {settings.OLLAMA_BASE_URL}; faltan modelos: {missing}. Ejecuta: {pulls}", False)
        else:
            _print_result(3, f"Ollama conectado en {settings.OLLAMA_BASE_URL}; modelos verificados: {settings.LLM_MODEL}, {settings.EMBED_MODEL}", True)
            passed_checks += 1
    except Exception as exc:  # noqa: BLE001
        _print_result(3, f"Ollama: {exc}", False)

    total_checks += 1
    try:
        start = time.perf_counter()
        embedding = embed_model.get_text_embedding(TEXT)
        elapsed = time.perf_counter() - start
        _print_result(4, f"Embedding generado; dimensión={len(embedding)}, tiempo={elapsed:.3f}s", True)
        passed_checks += 1
    except Exception as exc:  # noqa: BLE001
        _print_result(4, f"Embedding: {exc}", False)

    total_checks += 1
    try:
        start = time.perf_counter()
        response = llm.complete(PROMPT)
        elapsed = time.perf_counter() - start
        text = getattr(response, "text", str(response)).strip()
        _print_result(5, f"LLM respondió={text!r}, tiempo={elapsed:.3f}s", text == "OK")
        if text == "OK":
            passed_checks += 1
    except Exception as exc:  # noqa: BLE001
        _print_result(5, f"LLM: {exc}", False)

    total_checks += 1
    summary_ok = passed_checks == total_checks - 1
    if summary_ok:
        passed_checks += 1
    _print_result(6, f"Resumen final: {passed_checks}/{total_checks} comprobaciones superadas", summary_ok)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
