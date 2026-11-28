# Migración del esquema SQLite

Este documento describe el esquema real de la base de datos **SQLite** (`data/db/normativa.db`) y el proceso de migración hacia la arquitectura documental que soporta **categorías**, **familias** y **versiones**.

---

## 1. Estado previo (Iteración 1)

- Base de datos original: `data/db/normativa.db` (respaldo de seguridad en `data/backups/normativa_backup_iteracion_01.db`).
- Tablas originales: `documents`, `versions`, `chunks`, `traces`.
- En la Iteración 1, la tabla `versions` asumía una única versión activa global y no existía división entre reglamentos, procedimientos o formatos.

---

## 2. Esquema real implementado (Iteración 2 - Etapa 1)

El esquema implementado en `src/normativa/corpus/db.py` utiliza identificadores alfanuméricos (`TEXT PRIMARY KEY`) consistentes con las convenciones del proyecto:

```sql
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
    version_id TEXT,
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
```

---

## 3. Índices y Restricciones de Integridad

- **Regla 5 (Una versión activa por familia documental)**:
  Garantizada mediante índice condicional único en SQLite:
  ```sql
  CREATE UNIQUE INDEX IF NOT EXISTS idx_versions_active_per_family 
  ON versions(family_id) WHERE is_active = 1;
  ```
- **Integridad referencial**:
  - `idx_versions_family_id ON versions(family_id)`
  - `idx_chunks_family_id ON chunks(family_id)`
  - `idx_families_categoria_id ON families(categoria_id)`
  - `idx_documents_file_hash ON documents(file_hash)`

---

## 4. Semillas Predeterminadas (Default Seeds)

El método `init_db()` inicializa las categorías y familias institucionales básicas de la UTS:
- Categorías: `cat_reglamentos`, `cat_procedimientos`, `cat_formatos`.
- Familias: `fam_reglamento_tg` (RTG), `fam_p_dc_28` (P-DC-28), `fam_p_dc_29` (P-DC-29), `fam_f_dc_124` (F-DC-124), `fam_f_dc_125` (F-DC-125).

---

## 5. Scripts de Soporte

- **Migración inicial de corpus**: `scripts/migrate_v2_corpus.py`.
- **Restauración de emergencia**: `scripts/restore_v1_backup.py`.
- **Validación automatizada en tests**: `tests/test_etapa1_documental.py`, `tests/test_corpus_management.py`.
