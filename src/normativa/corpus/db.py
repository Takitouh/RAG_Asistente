from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from normativa.config import settings
from normativa.corpus.models import (
    DocumentCategory,
    DocumentFamily,
    DocumentMetadata,
    NormativeChunk,
    NormativeVersion,
    ProcessingStatus,
)


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
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id TEXT PRIMARY KEY,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                estado TEXT NOT NULL DEFAULT 'ACTIVO',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS families (
                id TEXT PRIMARY KEY,
                categoria_id TEXT NOT NULL,
                codigo TEXT NOT NULL UNIQUE,
                nombre TEXT NOT NULL,
                descripcion TEXT,
                perfil_procesamiento TEXT NOT NULL DEFAULT 'reglamento_estructurado',
                estado TEXT NOT NULL DEFAULT 'ACTIVO',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (categoria_id) REFERENCES categories(id) ON DELETE RESTRICT
            );

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
                family_id TEXT NOT NULL DEFAULT 'fam_reglamento_tg',
                perfil_procesamiento TEXT NOT NULL DEFAULT 'reglamento_estructurado',
                nombre TEXT NOT NULL,
                numero_version_institucional TEXT,
                numero_acuerdo TEXT,
                anio INTEGER,
                fecha_expedicion TEXT,
                procedencia TEXT,
                estado_vigencia TEXT,
                status TEXT NOT NULL,
                status_message TEXT,
                estado_revision TEXT NOT NULL DEFAULT 'PENDIENTE',
                fecha_revision TEXT,
                observaciones_revision TEXT,
                inconsistencia_identidad INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                activated_at TEXT,
                report_json TEXT,
                chunks_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
                FOREIGN KEY (family_id) REFERENCES families(id) ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                version_id TEXT NOT NULL,
                document_id TEXT NOT NULL,
                document_name TEXT NOT NULL,
                categoria_id TEXT,
                family_id TEXT,
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
                context_chunks_json TEXT NOT NULL DEFAULT '[]',
                authorized_versions_json TEXT NOT NULL DEFAULT '[]'
            );

            CREATE INDEX IF NOT EXISTS idx_versions_is_active ON versions(is_active);
            CREATE INDEX IF NOT EXISTS idx_chunks_version_id ON chunks(version_id);
            CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
            """
        )

        # Migraciones idempotentes para bases de datos existentes
        # Familias
        for col, col_type in [
            ("perfil_procesamiento", "TEXT NOT NULL DEFAULT 'reglamento_estructurado'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE families ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

        # Versiones
        for col, col_type in [
            ("family_id", "TEXT NOT NULL DEFAULT 'fam_reglamento_tg'"),
            ("perfil_procesamiento", "TEXT NOT NULL DEFAULT 'reglamento_estructurado'"),
            ("numero_version_institucional", "TEXT"),
            ("procedencia", "TEXT"),
            ("estado_revision", "TEXT NOT NULL DEFAULT 'PENDIENTE'"),
            ("fecha_revision", "TEXT"),
            ("observaciones_revision", "TEXT"),
            ("inconsistencia_identidad", "INTEGER NOT NULL DEFAULT 0"),
        ]:
            try:
                conn.execute(f"ALTER TABLE versions ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

        # Chunks
        for col, col_type in [
            ("categoria_id", "TEXT"),
            ("family_id", "TEXT"),
        ]:
            try:
                conn.execute(f"ALTER TABLE chunks ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

        # Traces
        for col, col_type in [
            ("query_type", "TEXT NOT NULL DEFAULT 'normative'"),
            ("context_chunks_json", "TEXT NOT NULL DEFAULT '[]'"),
            ("authorized_versions_json", "TEXT NOT NULL DEFAULT '[]'"),
        ]:
            try:
                conn.execute(f"ALTER TABLE traces ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass

        # Índices dependientes de nuevas columnas
        conn.execute("CREATE INDEX IF NOT EXISTS idx_versions_family_id ON versions(family_id);")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_versions_active_per_family ON versions(family_id) WHERE is_active = 1;")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_family_id ON chunks(family_id);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_families_categoria_id ON families(categoria_id);")

        # Sembrar categorías iniciales configurables
        default_categories = [
            ("cat_reglamentos", "Reglamentos", "Reglamentos institucionales y normativas generales de la UTS", "ACTIVO"),
            ("cat_procedimientos", "Procedimientos", "Procedimientos del Sistema Integrado de Gestión (SIG)", "ACTIVO"),
            ("cat_formatos", "Formatos Institucionales", "Formatos y guías oficiales para trabajo de grado", "ACTIVO"),
        ]
        for cat_id, cat_nombre, cat_desc, cat_est in default_categories:
            conn.execute(
                """
                INSERT INTO categories (id, nombre, descripcion, estado, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO NOTHING;
                """,
                (cat_id, cat_nombre, cat_desc, cat_est, now, now),
            )

        # Sembrar familias iniciales
        default_families = [
            ("fam_reglamento_tg", "cat_reglamentos", "RTG", "Reglamento de Trabajo de Grado", "Reglamento general de trabajo de grado de las UTS", "reglamento_estructurado", "ACTIVO"),
            ("fam_p_dc_28", "cat_procedimientos", "P-DC-28", "Presentación de la Propuesta de Trabajo de Grado", "Procedimiento para postulación y aprobación de propuestas de grado", "procedimiento_institucional", "ACTIVO"),
            ("fam_p_dc_29", "cat_procedimientos", "P-DC-29", "Presentación del Informe Final de Trabajo de Grado", "Procedimiento para entrega, evaluación y sustentación del informe final", "procedimiento_institucional", "ACTIVO"),
            ("fam_f_am_04", "cat_formatos", "F-AM-04", "Guía para Presentación de Trabajos de Grado", "Guía institucional para elaboración y presentación de documentos de grado", "formato_institucional", "ACTIVO"),
            ("fam_f_dc_124", "cat_formatos", "F-DC-124", "Propuesta de Trabajo de Grado", "Formato institucional para presentación de propuesta de grado", "formato_institucional", "ACTIVO"),
            ("fam_f_dc_125", "cat_formatos", "F-DC-125", "Informe Final de Trabajo de Grado", "Formato institucional para presentación de informe final de grado", "formato_institucional", "ACTIVO"),
            ("fam_f_dc_126", "cat_formatos", "F-DC-126", "Carta de Aceptación Director de Trabajo de Grado", "Carta y formato de aceptación y visto bueno de dirección", "formato_institucional", "ACTIVO"),
            ("fam_f_dc_127", "cat_formatos", "F-DC-127", "Acta de Inicio de Práctica", "Acta institucional para formalización del inicio de modalidad práctica", "formato_institucional", "ACTIVO"),
            ("fam_f_dc_128", "cat_formatos", "F-DC-128", "Evaluación Parcial de Práctica", "Formato institucional para seguimiento parcial de práctica", "formato_institucional", "ACTIVO"),
            ("fam_f_dc_129", "cat_formatos", "F-DC-129", "Evaluación Final de Práctica", "Formato institucional con rúbrica de evaluación final de práctica", "formato_institucional", "ACTIVO"),
            ("fam_f_dc_130", "cat_formatos", "F-DC-130", "Concepto del Director del Trabajo de Grado", "Concepto valorativo y autorización de sustentación por el director", "formato_institucional", "ACTIVO"),
            ("fam_f_dc_196", "cat_formatos", "F-DC-196", "Acta de Compromiso de Trabajo de Grado", "Acta de compromiso ético e institucional de los estudiantes de grado", "formato_institucional", "ACTIVO"),
        ]
        for fam_id, cat_id, fam_cod, fam_nom, fam_desc, fam_perf, fam_est in default_families:
            conn.execute(
                """
                INSERT INTO families (id, categoria_id, codigo, nombre, descripcion, perfil_procesamiento, estado, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    perfil_procesamiento = excluded.perfil_procesamiento,
                    nombre = excluded.nombre,
                    descripcion = excluded.descripcion;
                """,
                (fam_id, cat_id, fam_cod, fam_nom, fam_desc, fam_perf, fam_est, now, now),
            )

        # Actualizar datos de chunks huérfanos de familia/categoría
        conn.execute(
            """
            UPDATE chunks
            SET family_id = (SELECT versions.family_id FROM versions WHERE versions.id = chunks.version_id)
            WHERE chunks.family_id IS NULL;
            """
        )
        conn.execute(
            """
            UPDATE chunks
            SET categoria_id = (
                SELECT families.categoria_id
                FROM versions
                JOIN families ON versions.family_id = families.id
                WHERE versions.id = chunks.version_id
            )
            WHERE chunks.categoria_id IS NULL;
            """
        )


# ===========================================================================
# CATEGORÍAS DOCUMENTALES (CRUD)
# ===========================================================================


def save_category(category: DocumentCategory, db_path: str | Path | None = None) -> DocumentCategory:
    now = datetime.now(timezone.utc).isoformat()
    created_at = category.created_at or now
    updated_at = now
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO categories (id, nombre, descripcion, estado, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                nombre = excluded.nombre,
                descripcion = excluded.descripcion,
                estado = excluded.estado,
                updated_at = excluded.updated_at;
            """,
            (category.id, category.nombre, category.descripcion, category.estado, created_at, updated_at),
        )
    return get_category(category.id, db_path=db_path)  # type: ignore[return-value]


def get_category(cat_id: str, db_path: str | Path | None = None) -> DocumentCategory | None:
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM categories WHERE id = ?", (cat_id,)).fetchone()
        if not row:
            return None
        return DocumentCategory(
            id=row["id"],
            nombre=row["nombre"],
            descripcion=row["descripcion"],
            estado=row["estado"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )


def list_categories(include_inactive: bool = True, db_path: str | Path | None = None) -> list[DocumentCategory]:
    with get_connection(db_path) as conn:
        if include_inactive:
            rows = conn.execute("SELECT * FROM categories ORDER BY nombre ASC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM categories WHERE estado = 'ACTIVO' ORDER BY nombre ASC").fetchall()
        return [
            DocumentCategory(
                id=r["id"],
                nombre=r["nombre"],
                descripcion=r["descripcion"],
                estado=r["estado"],
                created_at=r["created_at"],
                updated_at=r["updated_at"],
            )
            for r in rows
        ]


def update_category(
    cat_id: str,
    nombre: str | None = None,
    descripcion: str | None = None,
    estado: str | None = None,
    db_path: str | Path | None = None,
) -> DocumentCategory:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM categories WHERE id = ?", (cat_id,)).fetchone()
        if not row:
            raise ValueError(f"No existe la categoría con id: '{cat_id}'")

        updates: list[str] = ["updated_at = ?"]
        params: list[Any] = [now]

        if nombre is not None:
            updates.append("nombre = ?")
            params.append(nombre.strip())
        if descripcion is not None:
            updates.append("descripcion = ?")
            params.append(descripcion.strip())
        if estado is not None:
            if estado not in ("ACTIVO", "INACTIVO"):
                raise ValueError("El estado de la categoría debe ser 'ACTIVO' o 'INACTIVO'")
            updates.append("estado = ?")
            params.append(estado)

        params.append(cat_id)
        conn.execute(f"UPDATE categories SET {', '.join(updates)} WHERE id = ?", params)
        updated_row = conn.execute("SELECT * FROM categories WHERE id = ?", (cat_id,)).fetchone()
        return DocumentCategory(
            id=updated_row["id"],
            nombre=updated_row["nombre"],
            descripcion=updated_row["descripcion"],
            estado=updated_row["estado"],
            created_at=updated_row["created_at"],
            updated_at=updated_row["updated_at"],
        )


def delete_category(cat_id: str, db_path: str | Path | None = None) -> bool:
    with get_connection(db_path) as conn:
        # Regla 16: Comprobar dependencias antes de eliminar
        fam_count = conn.execute("SELECT count(*) FROM families WHERE categoria_id = ?", (cat_id,)).fetchone()[0]
        if fam_count > 0:
            raise ValueError(f"No se puede eliminar la categoría '{cat_id}' porque contiene {fam_count} familias documentales asociadas.")
        res = conn.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        return res.rowcount > 0


# ===========================================================================
# FAMILIAS DOCUMENTALES (CRUD)
# ===========================================================================

def save_family(family: DocumentFamily, db_path: str | Path | None = None) -> DocumentFamily:
    now = datetime.now(timezone.utc).isoformat()
    created_at = family.created_at or now
    updated_at = now
    perfil = family.perfil_procesamiento or "reglamento_estructurado"
    with get_connection(db_path) as conn:
        # Validar categoría existente
        cat = conn.execute("SELECT id FROM categories WHERE id = ?", (family.categoria_id,)).fetchone()
        if not cat:
            raise ValueError(f"Categoría '{family.categoria_id}' no existe.")

        conn.execute(
            """
            INSERT INTO families (id, categoria_id, codigo, nombre, descripcion, perfil_procesamiento, estado, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                categoria_id = excluded.categoria_id,
                codigo = excluded.codigo,
                nombre = excluded.nombre,
                descripcion = excluded.descripcion,
                perfil_procesamiento = excluded.perfil_procesamiento,
                estado = excluded.estado,
                updated_at = excluded.updated_at;
            """,
            (family.id, family.categoria_id, family.codigo, family.nombre, family.descripcion, perfil, family.estado, created_at, updated_at),
        )
    return get_family(family.id, db_path=db_path)  # type: ignore[return-value]


def get_family(family_id: str, db_path: str | Path | None = None) -> DocumentFamily | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT f.*, c.nombre AS categoria_nombre
            FROM families f
            JOIN categories c ON f.categoria_id = c.id
            WHERE f.id = ?
            """,
            (family_id,),
        ).fetchone()
        if not row:
            return None
        keys = row.keys()
        return DocumentFamily(
            id=row["id"],
            categoria_id=row["categoria_id"],
            codigo=row["codigo"],
            nombre=row["nombre"],
            descripcion=row["descripcion"],
            estado=row["estado"],
            perfil_procesamiento=row["perfil_procesamiento"] if "perfil_procesamiento" in keys else "reglamento_estructurado",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            categoria_nombre=row["categoria_nombre"],
        )


def list_families(
    categoria_id: str | None = None,
    include_inactive: bool = True,
    db_path: str | Path | None = None,
) -> list[DocumentFamily]:
    with get_connection(db_path) as conn:
        query = """
            SELECT f.*, c.nombre AS categoria_nombre
            FROM families f
            JOIN categories c ON f.categoria_id = c.id
            WHERE 1=1
        """
        params: list[Any] = []
        if categoria_id:
            query += " AND f.categoria_id = ?"
            params.append(categoria_id)
        if not include_inactive:
            query += " AND f.estado = 'ACTIVO'"

        query += " ORDER BY f.nombre ASC"
        rows = conn.execute(query, params).fetchall()
        result = []
        for r in rows:
            keys = r.keys()
            result.append(
                DocumentFamily(
                    id=r["id"],
                    categoria_id=r["categoria_id"],
                    codigo=r["codigo"],
                    nombre=r["nombre"],
                    descripcion=r["descripcion"],
                    estado=r["estado"],
                    perfil_procesamiento=r["perfil_procesamiento"] if "perfil_procesamiento" in keys else "reglamento_estructurado",
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    categoria_nombre=r["categoria_nombre"],
                )
            )
        return result


def update_family(
    family_id: str,
    nombre: str | None = None,
    codigo: str | None = None,
    descripcion: str | None = None,
    categoria_id: str | None = None,
    perfil_procesamiento: str | None = None,
    estado: str | None = None,
    db_path: str | Path | None = None,
) -> DocumentFamily:
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT * FROM families WHERE id = ?", (family_id,)).fetchone()
        if not row:
            raise ValueError(f"No existe la familia documental con id: '{family_id}'")

        updates: list[str] = ["updated_at = ?"]
        params: list[Any] = [now]

        if categoria_id is not None:
            cat_row = conn.execute("SELECT id FROM categories WHERE id = ?", (categoria_id,)).fetchone()
            if not cat_row:
                raise ValueError(f"Categoría '{categoria_id}' no existe.")
            updates.append("categoria_id = ?")
            params.append(categoria_id)
        if codigo is not None:
            updates.append("codigo = ?")
            params.append(codigo.strip())
        if nombre is not None:
            updates.append("nombre = ?")
            params.append(nombre.strip())
        if descripcion is not None:
            updates.append("descripcion = ?")
            params.append(descripcion.strip())
        if perfil_procesamiento is not None:
            updates.append("perfil_procesamiento = ?")
            params.append(perfil_procesamiento.strip())
        if estado is not None:
            if estado not in ("ACTIVO", "INACTIVO"):
                raise ValueError("El estado de la familia debe ser 'ACTIVO' o 'INACTIVO'")
            updates.append("estado = ?")
            params.append(estado)

        params.append(family_id)
        conn.execute(f"UPDATE families SET {', '.join(updates)} WHERE id = ?", params)
        updated_row = conn.execute(
            """
            SELECT f.*, c.nombre AS categoria_nombre
            FROM families f
            JOIN categories c ON f.categoria_id = c.id
            WHERE f.id = ?
            """,
            (family_id,),
        ).fetchone()
        keys = updated_row.keys()
        return DocumentFamily(
            id=updated_row["id"],
            categoria_id=updated_row["categoria_id"],
            codigo=updated_row["codigo"],
            nombre=updated_row["nombre"],
            descripcion=updated_row["descripcion"],
            estado=updated_row["estado"],
            perfil_procesamiento=updated_row["perfil_procesamiento"] if "perfil_procesamiento" in keys else "reglamento_estructurado",
            created_at=updated_row["created_at"],
            updated_at=updated_row["updated_at"],
            categoria_nombre=updated_row["categoria_nombre"],
        )


def delete_family(family_id: str, db_path: str | Path | None = None) -> bool:
    with get_connection(db_path) as conn:
        # Regla 16: Comprobar dependencias antes de eliminar
        ver_count = conn.execute("SELECT count(*) FROM versions WHERE family_id = ?", (family_id,)).fetchone()[0]
        if ver_count > 0:
            raise ValueError(f"No se puede eliminar la familia '{family_id}' porque contiene {ver_count} versiones normativas asociadas.")
        res = conn.execute("DELETE FROM families WHERE id = ?", (family_id,))
        return res.rowcount > 0


# Alias para compatibilidad de nomenclatura
create_category = save_category
create_family = save_family


# ===========================================================================
# DOCUMENTOS Y DUPLICADOS SHA-256
# ===========================================================================

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


def detect_sha256_duplicates(file_hash: str, db_path: str | Path | None = None) -> list[dict[str, Any]]:
    """Busca si existen documentos ya registrados con la misma huella SHA-256 y sus versiones."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT d.id AS document_id, d.filename, d.file_hash, d.uploaded_at,
                   v.id AS version_id, v.nombre AS version_nombre, v.family_id,
                   v.numero_acuerdo, v.anio, v.is_active
            FROM documents d
            LEFT JOIN versions v ON d.id = v.document_id
            WHERE d.file_hash = ?
            """,
            (file_hash,),
        ).fetchall()
        return [dict(r) for r in rows]


# ===========================================================================
# VERSIONES DOCUMENTALES
# ===========================================================================

def _row_to_version(row: sqlite3.Row) -> NormativeVersion:
    keys = row.keys()
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
        family_id=row["family_id"] if "family_id" in keys else "fam_reglamento_tg",
        perfil_procesamiento=row["perfil_procesamiento"] if "perfil_procesamiento" in keys else "reglamento_estructurado",
        numero_version_institucional=row["numero_version_institucional"] if "numero_version_institucional" in keys else None,
        procedencia=row["procedencia"] if "procedencia" in keys else None,
        estado_revision=row["estado_revision"] if "estado_revision" in keys else "PENDIENTE",
        fecha_revision=row["fecha_revision"] if "fecha_revision" in keys else None,
        observaciones_revision=row["observaciones_revision"] if "observaciones_revision" in keys else None,
        inconsistencia_identidad=bool(row["inconsistencia_identidad"]) if "inconsistencia_identidad" in keys else False,
        activated_at=row["activated_at"],
        report_json=row["report_json"],
        chunks_count=row["chunks_count"],
        file_hash=row["file_hash"] if "file_hash" in keys else None,
        family_name=row["family_name"] if "family_name" in keys else None,
        categoria_id=row["categoria_id"] if "categoria_id" in keys else None,
        categoria_nombre=row["categoria_nombre"] if "categoria_nombre" in keys else None,
    )


def save_version(version: NormativeVersion, db_path: str | Path | None = None) -> None:
    status_str = version.status.value if isinstance(version.status, ProcessingStatus) else str(version.status)
    family_id = version.family_id or "fam_reglamento_tg"
    perfil = version.perfil_procesamiento or "reglamento_estructurado"
    with get_connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO versions (
                id, document_id, family_id, perfil_procesamiento, nombre, numero_version_institucional,
                numero_acuerdo, anio, fecha_expedicion, procedencia,
                estado_vigencia, status, status_message, estado_revision,
                fecha_revision, observaciones_revision, inconsistencia_identidad,
                is_active, created_at, updated_at, activated_at, report_json, chunks_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                document_id=excluded.document_id,
                family_id=excluded.family_id,
                perfil_procesamiento=excluded.perfil_procesamiento,
                nombre=excluded.nombre,
                numero_version_institucional=excluded.numero_version_institucional,
                numero_acuerdo=excluded.numero_acuerdo,
                anio=excluded.anio,
                fecha_expedicion=excluded.fecha_expedicion,
                procedencia=excluded.procedencia,
                estado_vigencia=excluded.estado_vigencia,
                status=excluded.status,
                status_message=excluded.status_message,
                estado_revision=excluded.estado_revision,
                fecha_revision=excluded.fecha_revision,
                observaciones_revision=excluded.observaciones_revision,
                inconsistencia_identidad=excluded.inconsistencia_identidad,
                is_active=excluded.is_active,
                updated_at=excluded.updated_at,
                activated_at=excluded.activated_at,
                report_json=excluded.report_json,
                chunks_count=excluded.chunks_count;
            """,
            (
                version.id,
                version.document_id,
                family_id,
                perfil,
                version.nombre,
                version.numero_version_institucional,
                version.numero_acuerdo,
                version.anio,
                version.fecha_expedicion,
                version.procedencia,
                version.estado_vigencia,
                status_str,
                version.status_message,
                version.estado_revision,
                version.fecha_revision,
                version.observaciones_revision,
                1 if version.inconsistencia_identidad else 0,
                1 if version.is_active else 0,
                version.created_at,
                version.updated_at,
                version.activated_at,
                version.report_json,
                version.chunks_count,
            ),
        )


def get_version(version_id: str, db_path: str | Path | None = None) -> NormativeVersion | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT v.*, d.file_hash, f.nombre AS family_name, f.categoria_id, c.nombre AS categoria_nombre
            FROM versions v
            LEFT JOIN documents d ON v.document_id = d.id
            LEFT JOIN families f ON v.family_id = f.id
            LEFT JOIN categories c ON f.categoria_id = c.id
            WHERE v.id = ?
            """,
            (version_id,),
        ).fetchone()
        if not row:
            return None
        return _row_to_version(row)


create_version = save_version



def list_versions(family_id: str | None = None, db_path: str | Path | None = None) -> list[NormativeVersion]:
    with get_connection(db_path) as conn:
        query = """
            SELECT v.*, d.file_hash, f.nombre AS family_name, f.categoria_id, c.nombre AS categoria_nombre
            FROM versions v
            LEFT JOIN documents d ON v.document_id = d.id
            LEFT JOIN families f ON v.family_id = f.id
            LEFT JOIN categories c ON f.categoria_id = c.id
            WHERE 1=1
        """
        params: list[Any] = []
        if family_id:
            query += " AND v.family_id = ?"
            params.append(family_id)

        query += " ORDER BY v.created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [_row_to_version(row) for row in rows]


def get_active_versions(db_path: str | Path | None = None) -> list[NormativeVersion]:
    """Retorna todas las versiones activas del corpus (una por cada familia activa con categoría activa)."""
    with get_connection(db_path) as conn:
        rows = conn.execute(
            """
            SELECT v.*, d.file_hash, f.nombre AS family_name, f.categoria_id, c.nombre AS categoria_nombre
            FROM versions v
            LEFT JOIN documents d ON v.document_id = d.id
            LEFT JOIN families f ON v.family_id = f.id
            LEFT JOIN categories c ON f.categoria_id = c.id
            WHERE v.is_active = 1
              AND (f.estado IS NULL OR f.estado = 'ACTIVO')
              AND (c.estado IS NULL OR c.estado = 'ACTIVO')
            ORDER BY f.nombre ASC, v.created_at DESC
            """
        ).fetchall()
        return [_row_to_version(row) for row in rows]


def get_active_version(db_path: str | Path | None = None) -> NormativeVersion | None:
    """
    Compatibilidad hacia atrás: retorna la versión activa de la familia Reglamento
    o la primera versión activa del corpus, siempre que su familia y categoría estén activas.
    """
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT v.*, d.file_hash, f.nombre AS family_name, f.categoria_id, c.nombre AS categoria_nombre
            FROM versions v
            LEFT JOIN documents d ON v.document_id = d.id
            LEFT JOIN families f ON v.family_id = f.id
            LEFT JOIN categories c ON f.categoria_id = c.id
            WHERE v.is_active = 1
              AND (f.estado IS NULL OR f.estado = 'ACTIVO')
              AND (c.estado IS NULL OR c.estado = 'ACTIVO')
            ORDER BY CASE WHEN v.family_id = 'fam_reglamento_tg' THEN 0 ELSE 1 END, v.created_at DESC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            return None
        return _row_to_version(row)


def get_active_version_by_family(family_id: str, db_path: str | Path | None = None) -> NormativeVersion | None:
    with get_connection(db_path) as conn:
        row = conn.execute(
            """
            SELECT v.*, d.file_hash, f.nombre AS family_name, f.categoria_id, c.nombre AS categoria_nombre
            FROM versions v
            LEFT JOIN documents d ON v.document_id = d.id
            LEFT JOIN families f ON v.family_id = f.id
            LEFT JOIN categories c ON f.categoria_id = c.id
            WHERE v.family_id = ? AND v.is_active = 1
              AND (f.estado IS NULL OR f.estado = 'ACTIVO')
              AND (c.estado IS NULL OR c.estado = 'ACTIVO')
            LIMIT 1
            """,
            (family_id,),
        ).fetchone()
        if not row:
            return None
        return _row_to_version(row)


def update_version_status(
    version_id: str,
    status: ProcessingStatus,
    message: str | None = None,
    report_json: str | None = None,
    chunks_count: int | None = None,
    estado_revision: str | None = None,
    fecha_revision: str | None = None,
    observaciones_revision: str | None = None,
    inconsistencia_identidad: bool | None = None,
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
        if estado_revision is not None:
            updates.append("estado_revision = ?")
            params.append(estado_revision)
        if fecha_revision is not None:
            updates.append("fecha_revision = ?")
            params.append(fecha_revision)
        if observaciones_revision is not None:
            updates.append("observaciones_revision = ?")
            params.append(observaciones_revision)
        if inconsistencia_identidad is not None:
            updates.append("inconsistencia_identidad = ?")
            params.append(1 if inconsistencia_identidad else 0)

        params.append(version_id)
        sql = f"UPDATE versions SET {', '.join(updates)} WHERE id = ?"
        conn.execute(sql, params)


def activate_version(version_id: str, db_path: str | Path | None = None) -> bool:
    """
    Activa atómicamente la versión especificada y desactiva la versión anterior de SU MISMA FAMILIA.
    Reglas de negocio:
    - Regla 5: Solo una versión activa por familia.
    - Regla 6: Múltiples familias activas simultáneamente.
    - Regla 7: Activar una nueva versión desactiva la versión anterior de esa misma familia.
    - Regla 8: La activación no desactiva versiones de otras familias.
    - Regla 10: No se permite activar si status != PROCESADO o estado_revision == 'RECHAZADO'.
    - Regla 11: No se permite activar si tiene inconsistencia de identidad documental.
    - Regla 14: Transaccional y protegida frente a concurrencia.
    """
    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        # Iniciar transacción inmediata para evitar colisiones concurrentes
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            """
            SELECT v.id, v.family_id, v.status, v.estado_revision, v.inconsistencia_identidad,
                   f.estado AS family_status, c.estado AS category_status
            FROM versions v
            LEFT JOIN families f ON v.family_id = f.id
            LEFT JOIN categories c ON f.categoria_id = c.id
            WHERE v.id = ?
            """,
            (version_id,),
        ).fetchone()

        if not row:
            raise ValueError(f"No existe la versión con id: '{version_id}'")

        if row["category_status"] and row["category_status"] != "ACTIVO":
            raise ValueError(f"No se puede activar la versión '{version_id}' porque su categoría documental está inactiva.")

        if row["family_status"] and row["family_status"] != "ACTIVO":
            raise ValueError(f"No se puede activar la versión '{version_id}' porque su familia documental está inactiva.")

        if row["status"] != ProcessingStatus.PROCESADO.value:
            raise ValueError(
                f"No se puede activar la versión '{version_id}' con estado '{row['status']}'. Debe estar PROCESADO."
            )

        if bool(row["inconsistencia_identidad"]):
            raise ValueError(
                f"No se puede activar la versión '{version_id}' porque presenta discrepancias de identidad documental no resueltas."
            )

        if row["estado_revision"] != "APROBADO":
            raise ValueError(
                f"No se puede activar la versión '{version_id}' porque su revisión documental no está APROBADA "
                f"(estado actual: '{row['estado_revision']}'). Solo se pueden activar versiones con estado_revision='APROBADO'."
            )

        family_id = row["family_id"]

        # Regla 7 & 8: Desactivar únicamente la versión previa de la misma familia
        conn.execute(
            "UPDATE versions SET is_active = 0, updated_at = ? WHERE family_id = ? AND is_active = 1",
            (now, family_id),
        )

        # Activar la versión seleccionada
        conn.execute(
            "UPDATE versions SET is_active = 1, activated_at = ?, updated_at = ? WHERE id = ?",
            (now, now, version_id),
        )
        return True


set_active_version = activate_version
list_active_versions = get_active_versions


def deactivate_version(version_id: str, db_path: str | Path | None = None) -> bool:

    now = datetime.now(timezone.utc).isoformat()
    with get_connection(db_path) as conn:
        row = conn.execute("SELECT is_active FROM versions WHERE id = ?", (version_id,)).fetchone()
        if not row:
            raise ValueError(f"No existe la versión con id: '{version_id}'")
        conn.execute("UPDATE versions SET is_active = 0, updated_at = ? WHERE id = ?", (now, version_id))
        return True


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


def update_version_metadata(
    version_id: str,
    nombre: str | None = None,
    numero_acuerdo: str | None = None,
    anio: int | None = None,
    fecha_expedicion: str | None = None,
    estado_vigencia: str | None = None,
    family_id: str | None = None,
    numero_version_institucional: str | None = None,
    procedencia: str | None = None,
    estado_revision: str | None = None,
    observaciones_revision: str | None = None,
    inconsistencia_identidad: bool | None = None,
    db_path: str | Path | None = None,
) -> NormativeVersion:
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
        if family_id is not None:
            # Validar familia existente
            fam_row = conn.execute("SELECT id FROM families WHERE id = ?", (family_id,)).fetchone()
            if not fam_row:
                raise ValueError(f"La familia documental '{family_id}' no existe.")
            updates.append("family_id = ?")
            params.append(family_id)
        if numero_version_institucional is not None:
            updates.append("numero_version_institucional = ?")
            params.append(numero_version_institucional)
        if procedencia is not None:
            updates.append("procedencia = ?")
            params.append(procedencia)
        if estado_revision is not None:
            updates.append("estado_revision = ?")
            params.append(estado_revision)
            updates.append("fecha_revision = ?")
            params.append(now)
        if observaciones_revision is not None:
            updates.append("observaciones_revision = ?")
            params.append(observaciones_revision)
        if inconsistencia_identidad is not None:
            updates.append("inconsistencia_identidad = ?")
            params.append(1 if inconsistencia_identidad else 0)

        params.append(version_id)
        conn.execute(
            f"UPDATE versions SET {', '.join(updates)} WHERE id = ?",
            params,
        )
        updated_row = conn.execute(
            """
            SELECT v.*, d.file_hash, f.nombre AS family_name, f.categoria_id, c.nombre AS categoria_nombre
            FROM versions v
            LEFT JOIN documents d ON v.document_id = d.id
            LEFT JOIN families f ON v.family_id = f.id
            LEFT JOIN categories c ON f.categoria_id = c.id
            WHERE v.id = ?
            """,
            (version_id,),
        ).fetchone()
        return _row_to_version(updated_row)


# ===========================================================================
# CHUNKS
# ===========================================================================

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
                chunk.categoria_id,
                chunk.family_id,
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
                categoria_id, family_id,
                capitulo_numero, capitulo_romano, capitulo_titulo,
                articulo_numero, articulo_ordinal, articulo_tipo,
                paragrafo_numero, inciso_marker,
                page_start, page_end, texto, ocr_confidence, location_hint, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                texto=excluded.texto,
                location_hint=excluded.location_hint,
                categoria_id=excluded.categoria_id,
                family_id=excluded.family_id;
            """,
            params,
        )


def get_chunks_by_version(version_id: str, db_path: str | Path | None = None) -> list[NormativeChunk]:
    with get_connection(db_path) as conn:
        rows = conn.execute("SELECT * FROM chunks WHERE version_id = ? ORDER BY page_start, rowid", (version_id,)).fetchall()
        keys = rows[0].keys() if rows else []
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
                categoria_id=row["categoria_id"] if "categoria_id" in keys else None,
                family_id=row["family_id"] if "family_id" in keys else None,
            )
            for row in rows
        ]


def delete_chunks_by_version(version_id: str, db_path: str | Path | None = None) -> None:
    with get_connection(db_path) as conn:
        conn.execute("DELETE FROM chunks WHERE version_id = ?", (version_id,))
