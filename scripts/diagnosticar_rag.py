"""Diagnóstico local de la Etapa 3. Las trazas se capturan en memoria."""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict
from pathlib import Path

from normativa.config import Settings, settings
from normativa.corpus.db import get_connection
from normativa.generation.generator import NormativeGenerator
from normativa.generation.rag_service import RAGService, authorized_versions
from normativa.retrieval.context_expander import procedure_subsection
from normativa.retrieval.models import RetrievalResult, RetrievedChunk
from normativa.retrieval.retriever import NormativeRetriever
from normativa.tracing.models import QueryTrace, elapsed

ROOT = Path(__file__).resolve().parents[1]
BASE_PROMPT = ROOT / "docs/iteracion_02/03_motor_rag/09_prompt_linea_base.txt"
BASE_OPTIONS = {
    "RAG_TOP_K": 6, "RAG_MAX_CONTEXT_CHUNKS": 12, "RAG_CONTEXT_TOKENS": 10240,
    "RAG_OUTPUT_TOKENS": 1400, "RAG_TEMPLATE_RESERVE_TOKENS": 256, "RAG_TOKEN_ESTIMATION": "bytes",
    "RAG_EXPANSION_UNITS": 2, "RAG_MAX_EXPANDED_CHUNKS": None, "RAG_MIN_SCORE": 0.0,
}


def list_chunks(config: Settings, *, document=None, version=None, article=None, paragraph=None,
                literal=None, section=None, activity=None, ids: list[str] | None = None,
                version_ids: list[str] | None = None) -> list[dict]:
    if version_ids is None:
        version_ids = [item.id for item in authorized_versions(config.SQLITE_PATH)]
    if not version_ids or ids == []:
        return []
    conditions = [f"c.version_id IN ({','.join('?' for _ in version_ids)})"]
    values = list(version_ids)
    if ids is not None:
        conditions.append(f"c.id IN ({','.join('?' for _ in ids)})")
        values.extend(ids)
    for column, value in (
        ("version_id", version), ("paragrafo_numero", paragraph), ("inciso_marker", literal),
        ("articulo_numero", activity if activity is not None else article),
    ):
        if value is not None:
            conditions.append(f"c.{column} = ? COLLATE NOCASE")
            values.append(value)
    if activity is not None:
        conditions.append("c.articulo_tipo = 'actividad_procedimiento'")
    elif article is not None:
        conditions.append("c.articulo_tipo IN ('reglamento', 'acuerdo')")
    with get_connection(config.SQLITE_PATH) as connection:
        rows = connection.execute(
            f"""
            SELECT c.id AS chunk_id, c.version_id, c.document_id, c.document_name, v.nombre AS version_name,
                   c.capitulo_numero, c.articulo_numero, c.articulo_tipo, c.paragrafo_numero, c.inciso_marker,
                   c.location_hint, c.page_start, c.page_end
            FROM chunks c JOIN versions v ON v.id = c.version_id AND v.document_id = c.document_id
            WHERE {' AND '.join(conditions)}
            ORDER BY c.document_name, c.page_start, c.articulo_numero, c.id
            """,
            values,
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        if document and not any(document.casefold() in item[key].casefold()
                                for key in ("document_name", "document_id", "version_name")):
            continue
        if section:
            location = item["location_hint"]
            section_label = re.search(r"\bNumeral\s+(\d+(?:\.\d+)*)(?![\d.])", location, re.I)
            if section not in (procedure_subsection(location), section_label[1] if section_label else None):
                continue
        result.append(item)
    return result


class ManualRetriever:
    """Solo localiza los IDs explícitos dentro del snapshot que recibe del servicio."""

    def __init__(self, config: Settings, ids: list[str]) -> None:
        self.config = config
        self.ids = ids

    def retrieve(self, query: str, authorized_version_ids: list[str], timings: dict) -> RetrievalResult:
        with elapsed(timings, "manual_lookup_ms"):
            rows = {row["chunk_id"]: row for row in list_chunks(
                self.config, ids=self.ids, version_ids=authorized_version_ids,
            )}
        chunks = [
            RetrievedChunk(cid, rows[cid]["version_id"], 0.0, {"origin": "manual"}, "", rows[cid]["location_hint"])
            for cid in dict.fromkeys(self.ids) if cid in rows
        ]
        return RetrievalResult(
            chunks[0].version_id if chunks else None, "Contexto manual", chunks=chunks,
            candidates=chunks, seeds=chunks, rankings={"manual": chunks},
        )


def automatic_retriever(config: Settings, **kwargs) -> NormativeRetriever:
    return NormativeRetriever(
        db_path=config.SQLITE_PATH, qdrant_url=config.QDRANT_URL, collection_name=config.QDRANT_COLLECTION,
        ollama_base_url=config.OLLAMA_BASE_URL, embed_model_name=config.EMBED_MODEL,
        top_k=config.RAG_TOP_K, min_score=config.RAG_MIN_SCORE, expansion_units=config.RAG_EXPANSION_UNITS,
        max_expanded_chunks=config.RAG_MAX_EXPANDED_CHUNKS, **kwargs,
    )


def diagnose(
    config: Settings, question: str, *, chunk_ids: list[str] | None = None, prompt: str | None = None,
    retriever=None, provider=None,
) -> dict:
    generator = NormativeGenerator(
        config=config, provider=provider, capture_request=True,
        **({"system_prompt": prompt} if prompt is not None else {}),
    )
    manual = chunk_ids is not None
    if manual:
        retriever = ManualRetriever(config, chunk_ids)
    saved: list[QueryTrace] = []
    service = RAGService(retriever=retriever or automatic_retriever(config), generator=generator,
                         db_path=config.SQLITE_PATH, trace_sink=saved.append)
    result = service.query(question)
    trace = saved[0]
    diagnostics = json.loads(trace.diagnostics_json)
    context = json.loads(trace.context_chunks_json)
    retrieved = json.loads(trace.retrieved_chunks_json)
    retrieval = diagnostics["retrieval"]
    generation = diagnostics["generation"]
    delivered = bool(generation.get("input_tokens")) and result.status != "technical_error"
    sent_ids = {chunk["chunk_id"] for chunk in context} if generation.get("request") else set()
    discard_keys = (
        "outside_initial_limit", "omitted_by_expansion", "omitted_by_count", "omitted_by_budget",
        "omitted_as_duplicate", "unverified_chunks",
    )
    discarded = {
        cid: reason for reason in discard_keys for cid in retrieval.get(reason, []) if cid not in sent_ids
    }
    missing = []
    if manual:
        for cid in dict.fromkeys(chunk_ids):
            if cid not in sent_ids:
                reason = discarded.get(cid, "no_autorizado_o_inexistente" if "manual" in retrieval.get("rankings", {}) else "sin_generacion")
                missing.append({"chunk_id": cid, "reason": reason})
                discarded[cid] = reason
        diagnostics["timings_ms"]["retrieval_ms"] = 0.0
    complete = delivered and not missing and sent_ids == set(chunk_ids or [])
    return {
        "question": question, "mode": "manual" if manual else "rag",
        "configuration": {key: value for key, value in config.model_dump().items()
                          if key.startswith("RAG_") or key in {"LLM_MODEL", "LLM_PROVIDER", "EMBED_MODEL", "LLM_TIMEOUT_SECONDS"}},
        "prompt_id": generator.prompt_id, "provider": diagnostics["provider"], "model": diagnostics["model"],
        "authorized_snapshot": json.loads(trace.authorized_versions_json),
        "requested_chunks": chunk_ids, "retrieved_chunks": retrieved, "selection": retrieval,
        "discarded": discarded, "context": context, "context_delivery_confirmed": delivered,
        "manual_context_complete": complete if manual else None,
        "manual_missing": missing, "response": result.answer, "status": result.status.value,
        "abstention_reason": result.abstention_reason, "unanswered_parts": result.unanswered_parts,
        "citations": [asdict(citation) for citation in result.citations],
        "generation": generation, "timings_ms": diagnostics["timings_ms"], "error": trace.error_message,
    }


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--db", type=Path, help="SQLite local")
    cli.add_argument("--salida", type=Path, help="Exportar JSON")
    modes = cli.add_subparsers(dest="mode", required=True)
    listing = modes.add_parser("listar")
    for name in ("documento", "version", "paragrafo", "literal", "numeral"):
        listing.add_argument(f"--{name}")
    location = listing.add_mutually_exclusive_group()
    for name in ("articulo", "actividad"):
        location.add_argument(f"--{name}", type=int)
    for mode in ("rag", "manual"):
        run = modes.add_parser(mode)
        run.add_argument("pregunta")
        run.add_argument("--perfil", choices=("actual", "base"), default="actual")
        run.add_argument("--prompt", type=Path)
        run.add_argument("--top-k", type=int)
        run.add_argument("--max-contexto", type=int)
        run.add_argument("--estimacion", choices=("bytes", "qwen2"))
        run.add_argument("--unidades-expansion", type=int)
        run.add_argument("--max-expandidos", type=int)
        run.add_argument("--ventana", type=int)
        run.add_argument("--salida-tokens", type=int)
        run.add_argument("--reserva-plantilla", type=int)
        run.add_argument("--min-score", type=float)
        if mode == "manual":
            run.add_argument("--chunk", action="append", required=True)
    return cli


def main(argv: list[str] | None = None) -> int:
    cli = parser()
    args = cli.parse_args(argv)
    overrides = BASE_OPTIONS.copy() if getattr(args, "perfil", None) == "base" else {}
    for arg, setting in (
        ("db", "SQLITE_PATH"), ("top_k", "RAG_TOP_K"), ("max_contexto", "RAG_MAX_CONTEXT_CHUNKS"),
        ("estimacion", "RAG_TOKEN_ESTIMATION"), ("unidades_expansion", "RAG_EXPANSION_UNITS"),
        ("max_expandidos", "RAG_MAX_EXPANDED_CHUNKS"), ("ventana", "RAG_CONTEXT_TOKENS"),
        ("salida_tokens", "RAG_OUTPUT_TOKENS"), ("reserva_plantilla", "RAG_TEMPLATE_RESERVE_TOKENS"),
        ("min_score", "RAG_MIN_SCORE"),
    ):
        value = getattr(args, arg, None)
        if value is not None:
            overrides[setting] = str(value) if arg == "db" else value
    try:
        config = Settings(**{**settings.model_dump(), **overrides})
        if not Path(config.SQLITE_PATH).is_file():
            raise ValueError("La base SQLite indicada no existe.")
        if args.salida and args.salida.resolve() == Path(config.SQLITE_PATH).resolve():
            raise ValueError("La salida JSON debe ser un archivo distinto de SQLite.")
        if args.mode == "listar":
            result = list_chunks(
                config, document=args.documento, version=args.version, article=args.articulo,
                paragraph=args.paragrafo, literal=args.literal, section=args.numeral, activity=args.actividad,
            )
        else:
            path = args.prompt or (BASE_PROMPT if args.perfil == "base" else None)
            result = diagnose(config, args.pregunta, chunk_ids=getattr(args, "chunk", None),
                              prompt=path.read_text(encoding="utf-8") if path else None)
    except (OSError, ValueError) as exc:
        cli.error(str(exc))
    rendered = json.dumps(result, indent=2, ensure_ascii=False)
    if args.salida:
        args.salida.write_text(rendered + "\n", encoding="utf-8")
        print(f"Resultado guardado en {args.salida}")
    else:
        print(rendered)
    if isinstance(result, dict) and result["status"] == "technical_error":
        return 1
    if args.mode == "manual" and not result["manual_context_complete"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
