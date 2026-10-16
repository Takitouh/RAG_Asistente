from __future__ import annotations


def _split_model_name(model: str) -> tuple[str, str | None]:
    if ":" not in model:
        return model, None
    name, tag = model.rsplit(":", 1)
    return name, tag


def ollama_model_matches(configured: str, available: str) -> bool:
    configured_name, configured_tag = _split_model_name(configured)
    available_name, available_tag = _split_model_name(available)

    if configured_tag is not None:
        return configured == available

    return configured_name == available_name and available_tag in (None, "", "latest")


def find_missing_ollama_models(configured_models: list[str], available_models: set[str]) -> list[str]:
    missing: list[str] = []
    for model in configured_models:
        if not any(ollama_model_matches(model, available) for available in available_models):
            missing.append(model)
    return missing

