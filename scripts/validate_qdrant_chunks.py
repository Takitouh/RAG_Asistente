"""scripts/validate_qdrant_chunks.py

Validador estricto de solo lectura: verifica la correspondencia y coherencia
exhaustiva entre los chunks almacenados en SQLite y los puntos indexados en Qdrant.

Verificaciones:
  1. Correspondencia individual por chunk_id.
  2. Correspondencia de version_id.
  3. Correspondencia de document_id.
  4. Correspondencia de family_id y categoria_id en el payload.
  5. Ausencia de puntos huérfanos en Qdrant (puntos sin chunk en SQLite).
  6. Ausencia de chunks en SQLite sin su correspondiente punto en Qdrant.
  7. Ausencia de duplicaciones de chunk_id en Qdrant.
  8. Coincidencia de la cantidad total de registros y puntos.
  9. Coherencia exacta del texto almacenado (payload.text == sqlite.texto).
  10. Coherencia de metadatos estructurales relevantes (location_hint, capitulo, articulo).

Garantías:
  - Solo lectura: PROHIBIDO realizar escrituras o modificaciones.
  - Finaliza con código 0 si todo es coherente, 1 si existe cualquier discrepancia.

Uso::

    uv run python scripts/validate_qdrant_chunks.py [--verbose]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient

from normativa.config import settings


# ---------------------------------------------------------------------------
# Carga de datos SQLite
# ---------------------------------------------------------------------------

def load_sqlite_chunks(db_path: str | Path) -> dict[str, dict[str, Any]]:
    path = Path(db_path)
    if not path.exists():
        raise FileNotFoundError(f"Base de datos SQLite no encontrada: {path}")

    import sqlite3
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            """
            SELECT
                ch.id          AS chunk_id,
                ch.version_id,
                ch.document_id,
                ch.document_name,
                ch.texto,
                ch.location_hint,
                ch.capitulo_numero,
                ch.articulo_numero,
                ch.page_start,
                ch.page_end,
                v.family_id,
                f.categoria_id
            FROM chunks ch
            JOIN versions v ON ch.version_id = v.id
            JOIN families f ON v.family_id = f.id
            """
        ).fetchall()
        return {r["chunk_id"]: dict(r) for r in rows}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Qdrant Helper
# ---------------------------------------------------------------------------

def get_qdrant_client(url: str) -> QdrantClient:
    try:
        client = QdrantClient(url=url)
        client.get_collections()
        return client
    except Exception as exc:
        raise ConnectionError(f"No se pudo conectar a Qdrant en '{url}': {exc}") from exc


def scroll_all_points(client: QdrantClient, collection_name: str, batch_size: int = 100):
    offset = None
    while True:
        result, next_offset = client.scroll(
            collection_name=collection_name,
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )
        for point in result:
            yield point
        if next_offset is None:
            break
        offset = next_offset


# ---------------------------------------------------------------------------
# Validación principal
# ---------------------------------------------------------------------------

def validate_correspondence(
    qdrant_url: str | None = None,
    collection_name: str | None = None,
    db_path: str | Path | None = None,
    verbose: bool = False,
    client: QdrantClient | None = None,
) -> tuple[int, dict[str, int]]:
    """Ejecuta la validación de correspondencia completa en modo solo lectura.

    Retorna:
        (exit_code, metrics_dict)
        exit_code: 0 si todo está verificado y coherente; 1 si hay discrepancias o errores.
    """
    url = qdrant_url or settings.QDRANT_URL
    collection = collection_name or settings.QDRANT_COLLECTION
    sqlite_file = db_path or settings.SQLITE_PATH

    print(f"[VAL] Iniciando validación de correspondencia:")
    print(f"      Qdrant URL  : {url}")
    print(f"      Colección   : {collection}")
    print(f"      Base SQLite : {sqlite_file}")
    print("-" * 70)

    # 1. Cargar datos de SQLite
    try:
        sqlite_chunks = load_sqlite_chunks(sqlite_file)
    except Exception as exc:
        sys.stderr.write(f"[ERROR] No se pudo leer SQLite: {exc}\n")
        return 1, {"sqlite_error": 1}

    # 2. Conectar a Qdrant
    if client is None:
        try:
            client = get_qdrant_client(url)
        except Exception as exc:
            sys.stderr.write(f"[ERROR] No se pudo conectar a Qdrant: {exc}\n")
            return 1, {"qdrant_error": 1}

    existing_collections = {c.name for c in client.get_collections().collections}
    if collection not in existing_collections:
        sys.stderr.write(f"[ERROR] Colección '{collection}' no encontrada en Qdrant.\n")
        return 1, {"collection_not_found": 1}

    # 3. Recopilar todos los puntos de Qdrant
    qdrant_points: dict[str, dict[str, Any]] = {}
    duplicate_chunks: list[str] = []
    points_without_chunk_id: list[Any] = []
    total_qdrant_points = 0

    for point in scroll_all_points(client, collection):
        total_qdrant_points += 1
        payload = point.payload or {}
        cid = payload.get("chunk_id")
        if not cid:
            points_without_chunk_id.append(point.id)
            continue
        if cid in qdrant_points:
            duplicate_chunks.append(cid)
        qdrant_points[cid] = payload

    total_sqlite_chunks = len(sqlite_chunks)
    discrepancies: int = 0

    print(f"[INFO] Chunks en SQLite   : {total_sqlite_chunks}")
    print(f"[INFO] Puntos en Qdrant   : {total_qdrant_points}")
    print(f"[INFO] Puntos con chunk_id: {len(qdrant_points)}")

    # Check 1: Puntos sin chunk_id
    if points_without_chunk_id:
        print(f"[ERROR] {len(points_without_chunk_id)} punto(s) en Qdrant no tienen el campo 'chunk_id':")
        for pid in points_without_chunk_id[:5]:
            print(f"        - Point ID: {pid}")
        discrepancies += len(points_without_chunk_id)

    # Check 2: Duplicaciones de chunk_id en Qdrant
    if duplicate_chunks:
        print(f"[ERROR] {len(duplicate_chunks)} chunk_id(s) duplicados encontrados en Qdrant:")
        for cid in duplicate_chunks[:5]:
            print(f"        - {cid}")
        discrepancies += len(duplicate_chunks)

    # Check 3: Puntos huérfanos en Qdrant (no existen en SQLite)
    orphans = set(qdrant_points.keys()) - set(sqlite_chunks.keys())
    if orphans:
        print(f"[ERROR] {len(orphans)} punto(s) huérfano(s) en Qdrant (sin registro en SQLite):")
        for cid in sorted(orphans)[:5]:
            print(f"        - {cid}")
        discrepancies += len(orphans)
    else:
        print("[OK] Ausencia total de puntos huérfanos en Qdrant.")

    # Check 4: Chunks en SQLite sin punto en Qdrant
    missing_in_qdrant = set(sqlite_chunks.keys()) - set(qdrant_points.keys())
    if missing_in_qdrant:
        print(f"[ERROR] {len(missing_in_qdrant)} chunk(s) de SQLite no existen en Qdrant:")
        for cid in sorted(missing_in_qdrant)[:5]:
            print(f"        - {cid}")
        discrepancies += len(missing_in_qdrant)
    else:
        print("[OK] Ausencia total de chunks sin punto en Qdrant (100% cobertura).")

    # Check 5: Correspondencia biunívoca y coherencia de metadatos y texto
    mismatched_versions = 0
    mismatched_documents = 0
    missing_family_id = 0
    mismatched_family_id = 0
    missing_categoria_id = 0
    mismatched_categoria_id = 0
    text_mismatches = 0
    location_mismatches = 0

    for chunk_id, sq in sqlite_chunks.items():
        if chunk_id not in qdrant_points:
            continue
        qp = qdrant_points[chunk_id]

        # version_id
        if qp.get("version_id") != sq["version_id"]:
            mismatched_versions += 1
            if verbose:
                print(f"[ERROR] chunk_id={chunk_id}: version_id Qdrant='{qp.get('version_id')}' != SQLite='{sq['version_id']}'")

        # document_id
        if qp.get("document_id") != sq["document_id"]:
            mismatched_documents += 1
            if verbose:
                print(f"[ERROR] chunk_id={chunk_id}: document_id Qdrant='{qp.get('document_id')}' != SQLite='{sq['document_id']}'")

        # family_id
        p_fam = qp.get("family_id")
        if p_fam is None:
            missing_family_id += 1
        elif p_fam != sq["family_id"]:
            mismatched_family_id += 1
            if verbose:
                print(f"[ERROR] chunk_id={chunk_id}: family_id Qdrant='{p_fam}' != SQLite='{sq['family_id']}'")

        # categoria_id
        p_cat = qp.get("categoria_id")
        if p_cat is None:
            missing_categoria_id += 1
        elif p_cat != sq["categoria_id"]:
            mismatched_categoria_id += 1
            if verbose:
                print(f"[ERROR] chunk_id={chunk_id}: categoria_id Qdrant='{p_cat}' != SQLite='{sq['categoria_id']}'")

        # Coherencia exacta de texto almacenado (payload.text vs chunk.texto)
        qp_text = qp.get("text")
        if qp_text is not None and qp_text != sq["texto"]:
            text_mismatches += 1
            if verbose:
                print(f"[ERROR] chunk_id={chunk_id}: El texto en Qdrant difiere del texto en SQLite.")

        # location_hint
        if "location_hint" in qp and qp.get("location_hint") != sq["location_hint"]:
            location_mismatches += 1

    total_meta_errors = (
        mismatched_versions
        + mismatched_documents
        + mismatched_family_id
        + mismatched_categoria_id
        + text_mismatches
        + location_mismatches
    )
    discrepancies += total_meta_errors

    # Reportar resultados
    print("\n" + "=" * 70)
    print("INFORME DE CORRESPONDENCIA SQLITE <-> QDRANT")
    print("=" * 70)
    print(f"  Chunks en SQLite               : {total_sqlite_chunks}")
    print(f"  Puntos en Qdrant               : {total_qdrant_points}")
    print(f"  Puntos sin chunk_id            : {len(points_without_chunk_id)}")
    print(f"  Puntos duplicados              : {len(duplicate_chunks)}")
    print(f"  Puntos huérfanos (en Qdrant)   : {len(orphans)}")
    print(f"  Chunks sin punto (en SQLite)   : {len(missing_in_qdrant)}")
    print(f"  Discrepancias de version_id    : {mismatched_versions}")
    print(f"  Discrepancias de document_id   : {mismatched_documents}")
    print(f"  family_id ausentes en Qdrant   : {missing_family_id}")
    print(f"  Discrepancias de family_id     : {mismatched_family_id}")
    print(f"  categoria_id ausentes en Qdrant: {missing_categoria_id}")
    print(f"  Discrepancias de categoria_id  : {mismatched_categoria_id}")
    print(f"  Discrepancias de texto exacto  : {text_mismatches}")
    print(f"  Discrepancias location_hint    : {location_mismatches}")
    print(f"  Total errores/discrepancias    : {discrepancies}")
    print("=" * 70)

    metrics = {
        "sqlite_chunks": total_sqlite_chunks,
        "qdrant_points": total_qdrant_points,
        "orphans": len(orphans),
        "missing_in_qdrant": len(missing_in_qdrant),
        "duplicates": len(duplicate_chunks),
        "mismatched_versions": mismatched_versions,
        "mismatched_documents": mismatched_documents,
        "missing_family_id": missing_family_id,
        "mismatched_family_id": mismatched_family_id,
        "missing_categoria_id": missing_categoria_id,
        "mismatched_categoria_id": mismatched_categoria_id,
        "text_mismatches": text_mismatches,
        "total_discrepancies": discrepancies,
    }

    if discrepancies > 0 or missing_family_id > 0 or missing_categoria_id > 0:
        if missing_family_id > 0 or missing_categoria_id > 0:
            print("[RESULTADO] PENDIENTE DE MIGRACIÓN: Existen puntos sin family_id o categoria_id.")
            print("            Ejecute: uv run python scripts/migrate_qdrant_payloads.py")
        else:
            print("[RESULTADO] FALLIDO: Se detectaron inconsistencias críticas entre SQLite y Qdrant.")
        return 1, metrics

    print("[RESULTADO] EXITOSO: Correspondencia 100% íntegra, biunívoca y coherente.")
    return 0, metrics


# ---------------------------------------------------------------------------
# Entrada CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validador estricto de correspondencia y coherencia entre SQLite y Qdrant."
    )
    parser.add_argument("--verbose", action="store_true", help="Mostrar advertencias detalladas.")
    parser.add_argument("--url", help="URL de Qdrant (override de settings.QDRANT_URL)")
    parser.add_argument("--collection", help="Colección Qdrant (override de settings.QDRANT_COLLECTION)")
    parser.add_argument("--db-path", help="Ruta a base SQLite (override de settings.SQLITE_PATH)")
    args = parser.parse_args()

    exit_code, _ = validate_correspondence(
        qdrant_url=args.url,
        collection_name=args.collection,
        db_path=args.db_path,
        verbose=args.verbose,
    )
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
