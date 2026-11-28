# Resultados de Pruebas Automatizadas — Etapa 2
## NORMATIVA-TG UTS

**Fecha de ejecución:** 2026-11-27  
**Entorno:** Python 3.12 (uv), SQLite3 estándar, Qdrant Client, pytest 9.1.1  
**Comando de verificación:** `.bin/uv run pytest tests/test_etapa2_procesamiento.py -v`

---

## 1. Resumen General

| Métrica | Valor |
|---|---|
| **Total de pruebas ejecutadas (Etapa 2)** | 38 |
| **Pruebas superadas (PASSED)** | **38** |
| **Pruebas fallidas (FAILED)** | **0** |
| **Tasa de éxito** | **100%** |
| **Tiempo de ejecución** | ~58 segundos |

---

## 2. Detalle de Pruebas por Categoría Funcional

### A. Extracción Híbrida y Metadatos de Página (§5)
- `test_extraction_text_layer_reglamento_real`: PASSED (27/27 páginas con capa de texto en Reglamento 2021).
- `test_extraction_per_page_decision`: PASSED (decisión independiente por página según umbral de caracteres).
- `test_extraction_mixed_pages`: PASSED (soporte para documentos con páginas mixtas texto/OCR).
- `test_page_metadata_preserved`: PASSED (preservación de número de página, método y confianza).

### B. Parser de Estructura Normativa y Verificación Reglamento 2021 (§8)
- `test_parser_reglamento_2021_articulos`: PASSED (74 artículos numerados 1 al 74).
- `test_parser_no_missing_articles`: PASSED (cero artículos faltantes).
- `test_parser_chapter_mapping`: PASSED (los 74 artículos tienen capítulo asignado).
- `test_parser_cross_page_articles`: PASSED (18 artículos preservan su rango multi-página).
- `test_parser_detects_missing_articles_synthetic`: PASSED (detección algorítmica de saltos en secuencia).
- `test_parser_detects_duplicate_articles_synthetic`: PASSED (detección de artículos duplicados).

### C. Perfiles de Procesamiento Documental (§6)
- `test_profile_registry_complete`: PASSED (todos los perfiles A, B, C y D registrados en `PROFILE_REGISTRY`).
- `test_profile_reglamento_processor`: PASSED (procesador de reglamento genera chunks y matriz completa).
- `test_profile_procedimiento_p_dc_28`: PASSED (extrae secciones 1 a 9 y actividades de P-DC-28).
- `test_profile_procedimiento_p_dc_29`: PASSED (extrae secciones 1 a 9 y actividades de P-DC-29).
- `test_profile_formato_institucional`: PASSED (procesador de formato tipifica secciones e instrucciones).
- `test_profile_general`: PASSED (procesador general segmenta por bloques y páginas).
- `test_profile_get_processor_by_string`: PASSED (resolución desacoplada mediante nombre string).
- `test_profile_invalid_raises`: PASSED (validación estricta de perfiles inexistentes).

### D. Estrategia de Segmentación y Chunks (§7)
- `test_segmentation_preserves_chapter_context`: PASSED (contexto de capítulo y artículo presente en cada chunk).
- `test_segmentation_no_empty_chunks`: PASSED (ningún chunk generado tiene cuerpo vacío).
- `test_segmentation_procedimiento_activities`: PASSED (relación actividad-responsable-registro preservada).
- `test_segmentation_all_formats`: PASSED (los 9 formatos institucionales producen chunks válidos).

### E. Controles de Calidad y Bloqueo de Activación (§10)
- `test_quality_checker_critical_missing_articles`: PASSED (artículos faltantes generan issue CRITICAL y bloquean activación).
- `test_quality_checker_empty_pages`: PASSED (detección de páginas sin texto).
- `test_quality_checker_low_ocr_confidence`: PASSED (advertencia por baja confianza OCR).
- `test_quality_checker_identity_mismatch`: PASSED (discrepancias acuerdo/año generan issue CRITICAL).
- `test_quality_checker_activation_blocked_by_critical`: PASSED (bloqueo preventivo ante issues críticos).
- `test_quality_checker_procedimiento_missing_section_7`: PASSED (ausencia de sección 7 bloquea procedimiento).

### F. Aislamiento de Versiones y Correspondencia SQLite-Qdrant (§11)
- `test_version_isolation_corpus_service`: PASSED (índice único impide dos versiones activas por familia).
- `test_historical_versions_preserved`: PASSED (las versiones históricas persisten íntegras).
- `test_sqlite_qdrant_correspondence_check`: PASSED (detección de desincronización entre SQLite y Qdrant).
- `test_sqlite_qdrant_correspondence_ok`: PASSED (validación de correspondencia 1:1).

### G. Inventario, Manifiesto y Matriz de Artículos (§3, §4, §8)
- `test_document_inventory_files_present`: PASSED (todos los archivos fuente requeridos están presentes).
- `test_document_sha256_stable`: PASSED (huellas criptográficas inalteradas).
- `test_word_to_pdf_conversion_manifest`: PASSED (manifiesto de los 9 formatos con estado EXITOSO).
- `test_article_matrix_completeness`: PASSED (matriz de 74 artículos con estado PENDIENTE_REVISION_HUMANA).
- `test_article_matrix_page_ranges`: PASSED (páginas inicial y final coherentes para cada artículo).
- `test_expected_articles_configurable`: PASSED (el conteo esperado no está hardcodeado).

---

## 3. Estado de la Suite Completa del Proyecto

Se ejecutó la suite general del backend que incluye pruebas de las iteraciones 1 y 2:
- **Total tests del proyecto:** 142 pruebas.
- **Resultado:** 142 PASSED.
- **Regresiones:** 0.
