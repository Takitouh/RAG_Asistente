from normativa.ollama_utils import ollama_model_matches


def test_ollama_model_matches_latest_alias() -> None:
    assert ollama_model_matches("bge-m3", "bge-m3:latest")


def test_ollama_model_matches_tagged_exactly() -> None:
    assert ollama_model_matches("qwen2.5:7b", "qwen2.5:7b")


def test_ollama_model_matches_tagged_does_not_accept_latest_alias() -> None:
    assert not ollama_model_matches("qwen2.5:7b", "qwen2.5:7b:latest")

