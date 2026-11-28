"""Experimentos locales sobre el mismo corpus ficticio para todos los perfiles."""
from __future__ import annotations

import argparse
from contextlib import closing
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter

from llama_index.embeddings.ollama import OllamaEmbedding
from qdrant_client import QdrantClient

from normativa.config import Settings, settings
from scripts.diagnosticar_rag import BASE_OPTIONS, BASE_PROMPT, automatic_retriever, diagnose
from test_etapa3_calidad import _CASES, _PROCEDURES, _RULES, _corpus

_ITEMS = ("medalla", "vasija", "arnés", "cántaro", "escala", "embudo", "bandeja",
          "pinza", "tamiz", "espejo", "polea", "molde", "cizalla")
_EXTRAS = [
    ("limite-base", 118, None, None, "Artículo 118", (
        "Para inspecciones de coral, el aviso se presenta como mínimo 3 días hábiles antes de la visita. "
        "El reporte se entrega como máximo 9 días calendario después de la visita."
    )),
    ("limite-excepcion", 118, "1", None, "Artículo 118 / Parágrafo 1", (
        "Para el grupo Nácar el aviso se presenta como mínimo 6 días hábiles antes de la visita. "
        "Se recomienda una etiqueta plateada, que es voluntaria."
    )),
    ("anexo", 126, None, None, "Artículo 126", "El inventario de arcilla contiene los elementos de los literales siguientes."),
    *[
        (f"anexo-{letter}", 126, None, letter, f"Artículo 126 / Literal {letter}",
         f"El inventario de arcilla exige incluir {name}. " + (
             "La descripción auxiliar identifica propiedades superficiales y referencias de conservación sin añadir requisitos. " * 10
         ))
        for letter, name in zip("abcdefghijklm", _ITEMS, strict=True)
    ],
]
CASES = [*_CASES,
    ("limites", "Para el grupo Nácar, ¿con qué antelación mínima se avisa una inspección de coral y cuál es el plazo máximo para presentar el reporte?"),
    ("enumeracion_larga", "Enumera todos los elementos del inventario de arcilla del artículo 126."),
    ("abstencion", "¿Cuál es el teléfono de emergencias para inspecciones de coral?"),
]
REQUIRED = {
    "condiciones": {"regla", "excepcion", "recomendacion"},
    "premisa": {"excepcion", "recomendacion"},
    "enumeracion": {f"lista-{letter}" for letter in "abcdefg"},
    "complemento": {"cierre", "acuse"},
    "parcial": {"excepcion"},
    "limites": {"limite-base", "limite-excepcion"},
    "enumeracion_larga": {f"anexo-{letter}" for letter in "abcdefghijklm"},
    "abstencion": set(),
}


def score(case: str, result: dict) -> dict:
    answer = result["response"].casefold()
    citations = {citation["chunk_id"] for citation in result["citations"]}
    found = {chunk["chunk_id"] for chunk in result["context"]}
    voluntary = "funda" in answer and any(
        term in answer for term in ("voluntari", "se recomienda", "no es obligatori", "no obligatori")
    )
    pending_matches = case != "parcial" or (
        bool(result["unanswered_parts"])
        and all("horario" in part.casefold() and "ámbar" not in part.casefold()
                for part in result["unanswered_parts"])
    )
    content = {
        "condiciones": "17" in answer and "ámbar" in answer and "4" in answer and "niebla" in answer and voluntary,
        "premisa": "4" in answer and voluntary,
        "enumeracion": all(word in answer for word in ("mapa", "brújula", "linterna", "cuerda", "sello", "lupa", "estuche")),
        "complemento": "libro de salida" in answer and "azul" in answer,
        "parcial": "4" in answer and "horario" in answer,
        "limites": bool(
            re.search(r"(?:mínim\w*|al menos)\D{0,18}6 días hábiles", answer)
            and re.search(r"(?:máxim\w*|a más tardar)\D{0,18}9 días calendario", answer)
            and "antes" in answer and "después" in answer
        ),
        "enumeracion_larga": all(word in answer for word in _ITEMS),
        "abstencion": not citations,
    }[case]
    target = {"parcial": "partial", "abstencion": "insufficient_evidence"}.get(case, "complete")
    return {"coverage": len(found & REQUIRED[case]), "required": len(REQUIRED[case]),
            "content": content, "status": result["status"] == target,
            "citations": REQUIRED[case] <= citations, "pending_matches_request": pending_matches,
            "citation_precision": len(citations & REQUIRED[case]) / len(citations) if citations else None,
            "passes": content and result["status"] == target and REQUIRED[case] <= citations and pending_matches}


def run(selected_profiles: list[str] | None = None) -> list[dict]:
    embedder = OllamaEmbedding(model_name=settings.EMBED_MODEL, base_url=settings.OLLAMA_BASE_URL)
    current = {**settings.model_dump(), "LLM_PROVIDER": "ollama"}
    baseline = BASE_PROMPT.read_text(encoding="utf-8")
    optimized = {
        **BASE_OPTIONS, "RAG_TOP_K": 10, "RAG_MAX_CONTEXT_CHUNKS": 14,
        "RAG_MAX_EXPANDED_CHUNKS": 12, "RAG_TOKEN_ESTIMATION": "qwen2",
    }
    sweep = [case for case in CASES if case[0] in {"enumeracion_larga", "complemento", "limites"}]
    repetitions = [case for case in CASES if case[0] in {"premisa", "parcial"}]
    profiles = [
        ("A", BASE_OPTIONS, baseline, CASES), ("B", optimized, baseline, CASES),
        ("C", BASE_OPTIONS, None, CASES), ("D", optimized, None, CASES),
        ("D5", {**optimized, "RAG_TOP_K": 5}, None, CASES),
        ("D15", {**optimized, "RAG_TOP_K": 15}, None, sweep),
        ("D_repeticion", optimized, None, repetitions),
    ]
    if selected_profiles:
        profiles = [profile for profile in profiles if profile[0] in selected_profiles]
    texts = [f"{location}\n{text}" for _, _, _, _, location, text in [*_RULES, *_EXTRAS, *_PROCEDURES]]
    vectors = dict(zip(texts, embedder.get_text_embedding_batch(texts), strict=True))
    embed_ms = {}
    for _, question in CASES:
        start = perf_counter()
        vectors[question] = embedder.get_text_embedding(question)
        embed_ms[question] = (perf_counter() - start) * 1000
    results = []
    with TemporaryDirectory(prefix="normativa-etapa3-") as temporary, closing(QdrantClient(":memory:")) as store:
        database = Path(temporary) / "experimento.db"
        _corpus(database, store, vectors.__getitem__, extra_rules=_EXTRAS)
        for profile, options, prompt, cases in profiles:
            config = Settings(**{**current, **options, "SQLITE_PATH": str(database), "QDRANT_COLLECTION": "calidad"})
            retriever = automatic_retriever(config, client=store, embed_fn=vectors.__getitem__)
            for case, question in cases:
                result = diagnose(config, question, prompt=prompt, retriever=retriever)
                result.update(profile=profile, case=case, assessment=score(case, result),
                              precomputed_embedding_ms=embed_ms[question])
                results.append(result)
                print(profile, case, result["assessment"], result["generation"].get("input_tokens"), flush=True)
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--perfil", choices=("A", "B", "C", "D", "D5", "D15", "D_repeticion"), action="append")
    args = parser.parse_args()
    args.salida.write_text(json.dumps(run(args.perfil), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
