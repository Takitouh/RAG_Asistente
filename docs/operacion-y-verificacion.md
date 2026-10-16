# Operación y verificación

Volver al [índice de documentación](README.md). Para conocer la arquitectura,
consulte [Arquitectura actual](arquitectura-actual.md).

## Configuración

Copie `.env.example` a `.env` si necesita cambiar valores. Los predeterminados
son locales:

| Variable | Valor por defecto |
| --- | --- |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| `LLM_MODEL` | `qwen2.5:7b` |
| `EMBED_MODEL` | `bge-m3` |
| `QDRANT_URL` | `http://localhost:6333` |
| `QDRANT_COLLECTION` | `normativa` |
| `SQLITE_PATH` | `data/db/normativa.db` |
| `DATA_DIR` | `data` |

El manifiesto actual requiere Python `>=3.13,<3.14`; esto contradice el
objetivo de Python 3.12 declarado en las instrucciones del proyecto. Consulte
[Estado actual](estado-actual.md) para el impacto.

## Ejecución

Desde la raíz del repositorio:

```bash
uv sync
docker compose up -d
uv run uvicorn normativa.api.main:app --port 8000
```

Procesar un PDF local:

```bash
uv run python scripts/parse_pdf.py data/pdfs/reglamento_trabajo_grado.pdf
```

Inspeccionar extracción y forzar OCR cuando corresponda:

```bash
uv run python scripts/inspect_pdf.py data/pdfs/reglamento_trabajo_grado.pdf
uv run python scripts/inspect_pdf.py data/pdfs/reglamento_trabajo_grado.pdf --force-ocr
```

Verificar dependencias y servicios:

```bash
uv run python scripts/check_env.py
uv run pytest
```

## Verificación ejecutada el 15 de octubre de 2026

`docker compose ps` mostró `normativa-qdrant` en ejecución, exponiendo el
puerto 6333. `scripts/check_env.py` completó 6 de 6 comprobaciones:

- RAM total 23.18 GiB, disponible 10.99 GiB y 12 CPU lógicas.
- Qdrant accesible, sin colecciones creadas (`[]`).
- Ollama accesible con `qwen2.5:7b` y `bge-m3`.
- Embedding generado con dimensión 1024 en 3.234 s.
- El LLM respondió `OK` en 6.216 s.

`uv run pytest` recopiló 17 pruebas: 16 correctas y 1 fallida. La falla está
en `test_reference_document_regression`: para el artículo 15, segundo
parágrafo, el parser produjo el inciso `a` pero la prueba espera `a` y `b`.
También se emitió una advertencia de deprecación de `starlette.testclient` por
su uso de `httpx`.

La suite no está completamente verde; no debe presentarse como validación total
del pipeline. El seguimiento recomendado está en
[Pendientes y brechas](pendientes-y-brechas.md).

## Artefactos procesados existentes

Para `reglamento_trabajo_grado.pdf` están presentes estos productos locales:

- `data/processed/reglamento_trabajo_grado_pages.json`: caché de páginas y
  líneas extraídas.
- `data/processed/reglamento_trabajo_grado_cleaning_log.txt`: líneas retiradas
  y anomalías de limpieza.
- `data/processed/reglamento_trabajo_grado_parsed.json`: representación
  serializada del documento procesado.
- `data/processed/reglamento_trabajo_grado_parsed_preview.md`: vista legible
  del documento parseado.
- `data/processed/reglamento_trabajo_grado_parse_report.txt`: reparaciones,
  anomalías y conteos del parseo.

Como `data/` está ignorado por Git, estos artefactos son locales y no están
garantizados en una clonación nueva.
