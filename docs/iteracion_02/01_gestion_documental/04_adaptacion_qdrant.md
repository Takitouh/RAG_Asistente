# Adaptación de Qdrant para la arquitectura documental de la Etapa 1

Este documento explica los cambios aplicados en la colección **Qdrant** (`normativa`) para que el motor RAG pueda filtrar y recuperar fragmentos (chunks) sobre el conjunto de versiones autorizadas activas, respetando las reglas de negocio de la Etapa 1.

---

## 1. Metadatos de los puntos en Qdrant

Cada vector almacenado en la colección `normativa` (1024 dimensiones, métrica `Cosine`) representa un fragmento (`chunk`) y cuenta con el siguiente payload JSON generado por `NormativeChunk.to_payload()` en `src/normativa/corpus/models.py`:

```json
{
  "chunk_id": "uts_tg_2019_art_1_cuerpo",
  "version_id": "uts_tg_2019",
  "family_id": "fam_reglamento_tg",
  "categoria_id": "cat_reglamentos",
  "document_id": "doc_9fb89774cb",
  "document_name": "uts_tg_2019.pdf",
  "capitulo_numero": 1,
  "capitulo_romano": "I",
  "capitulo_titulo": "DISPOSICIONES GENERALES",
  "articulo_numero": 1,
  "articulo_ordinal": null,
  "articulo_tipo": "ARTICULO",
  "paragrafo_numero": null,
  "inciso_marker": null,
  "page_start": 4,
  "page_end": 4,
  "text": "El presente reglamento tiene por objeto normar las actividades...",
  "ocr_confidence": 98.5,
  "location_hint": "Capítulo I, Artículo 1"
}
```

---

## 2. Índices de Filtrado en Qdrant (Payload Schema)

Para garantizar un filtrado eficiente y determinista sin escaneo completo de vectores, se configuran índices de tipo `KEYWORD` en Qdrant sobre los campos:
- `version_id` (KEYWORD)
- `family_id` (KEYWORD)
- `categoria_id` (KEYWORD)

Son creados automáticamente por `QdrantCorpusIndexer.ensure_collection()` en `src/normativa/retrieval/indexer.py`.

---

## 3. Filtrado obligatorio en las consultas RAG

En `src/normativa/retrieval/retriever.py`, la recuperación semántica aplica un filtro estricto por `version_id` basado en el snapshot inmutable de versiones activas autorizadas:

```python
filter = qdrant_models.Filter(
    must=[
        qdrant_models.FieldCondition(
            key="version_id",
            match=qdrant_models.MatchAny(any=authorized_version_ids),
        )
    ]
)
```

### Reglas clave:
1. **Aislamiento**: Si no hay versiones autorizadas activas (`authorized_version_ids = []`), el sistema se abstiene inmediatamente sin consultar Qdrant.
2. **Snapshot inmutable**: Las versiones autorizadas se capturan al inicio de la consulta en `RAGService.query()`, protegiendo la respuesta frente a activaciones concurrentes mientras dura la consulta.
3. **Exclusión de categorías y familias inactivas**: Si una categoría o familia documental se encuentra en estado `INACTIVO`, sus versiones activas se excluyen automáticamente del conjunto `authorized_version_ids`.

---

## 4. Scripts Oficiales de Migración y Validación

El proyecto dispone de dos herramientas de mantenimiento:

### 4.1. Migración de payloads (`scripts/migrate_qdrant_payloads.py`)
- Script idempotente que incorpora `family_id` y `categoria_id` en los payloads de Qdrant.
- **Pre-validación en memoria**: Antes de realizar cualquier escritura, valida la correspondencia de todos los puntos contra SQLite. Si existe alguna inconsistencia (ej. puntos huérfanos o desajustes de versión), aborta sin modificar datos.
- Utiliza la configuración oficial (`normativa.config.settings`) y el cliente oficial `QdrantClient.set_payload(..., wait=True)`.
- Modos:
  - `--dry-run`: Simula la migración y contabiliza cambios previstos sin escribir.
  - `--verify`: Modo de solo lectura de verificación.
  - Ejecución estándar: Aplica las actualizaciones en Qdrant.

### 4.2. Validador de correspondencia (`scripts/validate_qdrant_chunks.py`)
- Script de **solo lectura**.
- Comprueba:
  1. Correspondencia individual por `chunk_id`.
  2. Coherencia de `version_id`, `document_id`, `family_id` y `categoria_id`.
  3. Ausencia de puntos huérfanos en Qdrant.
  4. Ausencia de chunks sin punto en Qdrant (100% cobertura).
  5. Ausencia de identificadores duplicados.
  6. Coherencia exacta del texto almacenado (`payload.text == sqlite.texto`).
  7. Retorna código de salida `0` si todo está íntegro y `1` si hay discrepancias.

---

## 5. Pruebas Automatizadas

- `tests/test_migrate_qdrant_payloads.py`: Pruebas de dry-run, pre-validación de aborto ante huérfanos, idempotencia y tolerancia a fallos.
- `tests/test_validate_qdrant_chunks.py`: Pruebas de detección de discrepancias, ausencia de puntos, textos modificados y payloads incompletos.
