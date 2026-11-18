from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from normativa.config import settings
from normativa.corpus.models import DocumentMetadata, NormativeChunk, NormativeVersion, ProcessingStatus


def _get_path(path: str | Path | None = None) -> Path:
    if path is not None:
        target = Path(path)
    else:
        target = Path(settings.SQLITE_PATH)
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = _get_path(db_path)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str | Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_hash TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                uploaded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS versions (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                nombre TEXT NOT NULL,
                numero_acuerdo TEXT,
                anio INTEGER,
                fecha_expedicion TEXT,
                estado_vigencia TEXT,
                status TEXT NOT NULL,
                status_message TEXT,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                activated_at TEXT,
                report_json TEXT,
                chunks_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                version_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                document_name TEXT NOT NULL,
                capitulo_numero INTEGER,
                capitulo_romano TEXT,
                capitulo_titulo TEXT,
                articulo_numero INTEGER,
                articulo_ordinal TEXT,
                articulo_tipo TEXT NOT NULL,
                paragrafo_numero TEXT,
                inciso_marker TEXT,
                page_start INTEGER NOT NULL,
                page_end INTEGER NOT NULL,
                texto TEXT NOT NULL,
                ocr_confidence REAL,
                location_hint TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (version_id) REFERENCES versions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS traces (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                version_id TEXT NOT NULL,
                query TEXT NOT NULL,
                response TEXT NOT NULL,
                abstained INTEGER NOT NULL DEFAULT 0,
                retrieved_chunks_json TEXT NOT NULL DEFAULT '[]',
                citations_json TEXT NOT NULL DEFAULT '[]',
                abstention_reason TEXT,
                retrieval_ms REAL NOT NULL DEFAULT 0.0,
                generation_ms REAL NOT NULL DEFAULT 0.0,
                total_ms REAL NOT NULL DEFAULT 0.0,
                execution_status TEXT NOT NULL DEFAULT 'ok',
                error_message TEXT,
                latency_ms REAL NOT NULL DEFAULT 0.0,
                query_type TEXT NOT NULL DEFAULT 'normative',
                context_chunks_json TEXT NOT NULL DEFAULT '[]'
            );

            CREATE INDEX IF NOT EXISTS idx_versions_is_active ON versions(is_active);
            CREATE INDEX IF NOT EXISTS idx_chunks_version_id ON chunks(version_id);
            CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
            """
        )
        # Migraciones controladas e idempotentes
        try:
            conn.execute("ALTER TABLE traces ADD COLUMN query_type TEXT NOT NULL DEFAULT 'normative'")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute("ALTER TABLE traces ADD COLUMN context_chunks_json TEXT NOT NULL DEFAULT '[]'")
        except sqlite3.OperationalError:
            pass


def save_document(doc: DocumentMetadata, db_path: str | Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO documents (id, filename, file_path, file_hash, file_size_bytes, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                filename=excluded.filename,
                file_path=excluded.file_path,
                file_hash=excluded.file_hash,
                file_size_bytes=excluded.file_size_bytes;
            """,
            (doc.id, doc.filename, doc.file_path, doc.file_hash, doc.file_size_bytes, doc.uploaded_at),
        )


def get_document(doc_id: str, db_path: str | Path | None = None) -> DocumentMetadata | None:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            return None
        return DocumentMetadata(
            id=row["id"],
            filename=row["filename"],
            file_path=row["file_path"],
            file_hash=row["file_hash"],
            file_size_bytes=row["file_size_bytes"],
            uploaded_at=row["uploaded_at"],
        )


def list_documents(db_path: str | Path | None = None) -> list[DocumentMetadata]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM documents ORDER BY uploaded_at DESC").fetchall()
        return [
            DocumentMetadata(
                id=row["id"],
                filename=row["filename"],
                file_path=row["file_path"],
                file_hash=row["file_hash"],
                file_size_bytes=row["file_size_bytes"],
                uploaded_at=row["uploaded_at"],
            )
            for row in rows
        ]


def save_version(version: NormativeVersion, db_path: str | Path | None = None) -> None:
    status_str = version.status.value if isinstance(version.status, ProcessingStatus) else str(version.status)
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO versions (
                id, document_id, nombre, numero_acuerdo, anio, fecha_expedicion,
                estado_vigencia, status, status_message, is_active, created_at,
                updated_at, activated_at, report_json, chunks_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                document_id=excluded.document_id,
                nombre=excluded.nombre,
                numero_acuerdo=excluded.numero_acuerdo,
                anio=excluded.anio,
                fecha_expedicion=excluded.fecha_expedicion,
                estado_vigencia=excluded.estado_vigencia,
                status=excluded.status,
                status_message=excluded.status_message,
                is_active=excluded.is_active,
                updated_at=excluded.updated_at,
                activated_at=excluded.activated_at,
                report_json=excluded.report_json,
                chunks_count=excluded.chunks_count;
            """,
            (
                version.id,
                version.document_id,
                version.nombre,
                version.numero_acuerdo,
                version.anio,
                version.fecha_expedicion,
                version.estado_vigencia,
                status_str,
                version.status_message,
                1 if version.is_active else 0,
                version.created_at,
                version.updated_at,
                version.activated_at,
                version.report_json,
                version.chunks_count,
            ),
        )


def _row_to_version(row: sqlite3.Row) -> NormativeVersion:
    return NormativeVersion(
        id=row["id"],
        document_id=row["document_id"],
        nombre=row["nombre"],
        numero_acuerdo=row["numero_acuerdo"],
        anio=row["anio"],
        fecha_expedicion=row["fecha_expedicion"],
        estado_vigencia=row["estado_vigencia"],
        status=ProcessingStatus(row["status"]),
        status_message=row["status_message"],
        is_active=bool(row["is_active"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        activated_at=row["activated_at"],
        report_json=row["report_json"],
        chunks_count=row["chunks_count"],
    )


def get_version(version_id: str, db_path: str | Path | None = None) -> NormativeVersion | None:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,)).fetchone()
        if not row:
            return None
        return _row_to_version(row)


def list_versions(db_path: str | Path | None = None) -> list[NormativeVersion]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM versions ORDER BY created_at DESC").fetchall()
        return [_row_to_version(row) for row in rows]


def update_version_status(
    version_id: str,
    status: ProcessingStatus,
    message: str | None = None,
    report_json: str | None = None,
    chunks_count: int | None = None,
    db_path: str | Path | None = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    status_str = status.value if isinstance(status, ProcessingStatus) else str(status)
    with get_connection(db_path) as conn:
        updates = ["status = ?", "updated_at = ?"]
        params: list[Any] = [status_str, now]

        if message is not None:
            updates.append("status_message = ?")
            params.append(message)
        if report_json is not None:
            updates.append("report_json = ?")
            params.append(report_json)
        if chunks_count is not None:
            updates.append("chunks_count = ?")
            params.append(chunks_count)

        params.append(version_id)
        sql = f"UPDATE versions SET {', '.join(updates)} WHERE id = ?"
        conn.execute(sql, params)


def activate_version(version_id: str, db_path: str | Path | None = None) -> bool:
    """
    Atomically activates the specified version and deactivates all others.
    A version can only be activated if its status is PROCESADO.
    """
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT status FROM versions WHERE id = ?", (version_id,)).fetchone()
        if not row:
            raise ValueError(f"No existe la versión con id: '{version_id}'")
        if row["status"] != ProcessingStatus.PROCESADO.value:
            raise ValueError(
                f"No se puede activar la versión '{version_id}' con estado '{row['status']}'. Debe estar PROCESADO."
            )

        # Atomic transaction: set all to 0, then activate target
        conn.execute("UPDATE versions SET is_active = 0 WHERE is_active = 1")
        conn.execute(
            "UPDATE versions SET is_active = 1, activated_at = ?, updated_at = ? WHERE id = ?",
            (now, now, version_id),
        )
        return True


def deactivate_version(version_id: str, db_path: str | Path | None = None) -> bool:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT is_active FROM versions WHERE id = ?", (version_id,)).fetchone()
        if not row:
            raise ValueError(f"No existe la versión con id: '{version_id}'")
        conn.execute("UPDATE versions SET is_active = 0, updated_at = ? WHERE id = ?", (now, version_id))
        return True


def get_active_version(db_path: str | Path | None = None) -> NormativeVersion | None:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM versions WHERE is_active = 1").fetchone()
        if not row:
            return None
        return _row_to_version(row)


def delete_version(version_id: str, db_path: str | Path | None = None) -> bool:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT is_active FROM versions WHERE id = ?", (version_id,)).fetchone()
        if not row:
            return False
        if bool(row["is_active"]):
            raise ValueError("No se puede eliminar la versión activa. Desactívela antes de retirarla.")
        conn.execute("DELETE FROM chunks WHERE version_id = ?", (version_id,))
        conn.execute("DELETE FROM versions WHERE id = ?", (version_id,))
        return True


def insert_chunks(chunks: list[NormativeChunk], db_path: str | Path | None = None) -> None:
    if not chunks:
        return
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        params = [
            (
                chunk.chunk_id,
                chunk.version_id,
                chunk.document_id,
                chunk.document_name,
                chunk.capitulo_numero,
                chunk.capitulo_romano,
                chunk.capitulo_titulo,
                chunk.articulo_numero,
                chunk.articulo_ordinal,
                chunk.articulo_tipo,
                chunk.paragrafo_numero,
                chunk.inciso_marker,
                chunk.page_start,
                chunk.page_end,
                chunk.texto,
                chunk.ocr_confidence,
                chunk.location_hint,
                now,
            )
            for chunk in chunks
        ]
        conn.executemany(
            """
            INSERT INTO chunks (
                id, version_id, document_id, document_name,
                capitulo_numero, capitulo_romano, capitulo_titulo,
                articulo_numero, articulo_ordinal, articulo_tipo,
                paragrafo_numero, inciso_marker,
                page_start, page_end, texto, ocr_confidence, location_hint, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                texto=excluded.texto,
                location_hint=excluded.location_hint;
            """,
            params,
        )


def get_chunks_by_version(version_id: str, db_path: str | Path | None = None) -> list[NormativeChunk]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM chunks WHERE version_id = ? ORDER BY page_start, id", (version_id,)).fetchall()
        return [
            NormativeChunk(
                chunk_id=row["id"],
                version_id=row["version_id"],
                document_id=row["document_id"],
                document_name=row["document_name"],
                capitulo_numero=row["capitulo_numero"],
                capitulo_romano=row["capitulo_romano"],
                capitulo_titulo=row["capitulo_titulo"],
                articulo_numero=row["articulo_numero"],
                articulo_ordinal=row["articulo_ordinal"],
                articulo_tipo=row["articulo_tipo"],
                paragrafo_numero=row["paragrafo_numero"],
                inciso_marker=row["inciso_marker"],
                page_start=row["page_start"],
                page_end=row["page_end"],
                texto=row["texto"],
                ocr_confidence=row["ocr_confidence"],
                location_hint=row["location_hint"],
            )
            for row in rows
        ]


def delete_chunks_by_version(version_id: str, db_path: str | Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM chunks WHERE version_id = ?", (version_id,))


def update_version_metadata(
    version_id: str,
    nombre: str | None = None,
    numero_acuerdo: str | None = None,
    anio: int | None = None,
    fecha_expedicion: str | None = None,
    estado_vigencia: str | None = None,
    db_path: str | Path | None = None,
) -> NormativeVersion:
    """Actualiza los metadatos editables de una versión normativa.

    Permite al administrador corregir la información suministrada antes o
    después del procesamiento, sin reiniciar el pipeline.  Los campos con
    valor ``None`` no se modifican.

    Returns:
        NormativeVersion actualizada.

    Raises:
        ValueError: si no existe la versión.
    """
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,)).fetchone()
        if not row:
            raise ValueError(f"No existe la versión con id: '{version_id}'")

        updates: list[str] = ["updated_at = ?"]
        params: list[Any] = [now]

        if nombre is not None:
            updates.append("nombre = ?")
            params.append(nombre)
        if numero_acuerdo is not None:
            updates.append("numero_acuerdo = ?")
            params.append(numero_acuerdo)
        if anio is not None:
            updates.append("anio = ?")
            params.append(anio)
        if fecha_expedicion is not None:
            updates.append("fecha_expedicion = ?")
            params.append(fecha_expedicion)
        if estado_vigencia is not None:
            updates.append("estado_vigencia = ?")
            params.append(estado_vigencia)

        params.append(version_id)
        conn.execute(
            f"UPDATE versions SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        updated_row = conn.execute("SELECT * FROM versions WHERE id = ?", (version_id,)).fetchone()
        return _row_to_version(updated_row)
