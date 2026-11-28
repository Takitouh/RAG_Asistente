# Verificación y Cierre Final de la Etapa 1 — NORMATIVA-TG UTS

**Proyecto**: NORMATIVA-TG UTS — Asistente RAG para el Reglamento de Trabajo de Grado  
**Propuesta de Grado**: Código 65-2026-127 (F-DC-124)  
**Iteración**: 02 — Etapa 1 de 5 (Gestión documental y versionamiento)  
**Fecha de Auditoría**: 27 de noviembre de 2026  

---

## 1. Resumen Ejecutivo del Cierre de la Etapa 1

Se completó la auditoría exhaustiva, corrección e implementación de la Etapa 1 del proyecto NORMATIVA-TG UTS. Se remediaron todas las inconsistencias detectadas en la implementación previa, se estandarizó la configuración centralizada mediante `normativa.config.settings`, se corrigieron los scripts de migración y validación de Qdrant, y se verificó el 100% de la funcionalidad requerida en backend y frontend.

---

## 2. Matriz de Estado Detallada por Componente

| Componente / Funcionalidad | Estado | Evidencia de Verificación |
| :--- | :---: | :--- |
| **Categorías documentales dinámicas (CRUD)** | **Implementado y Verificado** | `src/normativa/corpus/db.py`, `src/normativa/api/admin.py`, `tests/test_etapa1_documental.py`. |
| **Familias documentales dinámicas (CRUD)** | **Implementado y Verificado** | `src/normativa/corpus/db.py`, `src/normativa/api/admin.py`, `tests/test_etapa1_documental.py`. |
| **Versiones asociadas a familias** | **Implementado y Verificado** | FK `versions.family_id` referenciando `families(id)`. |
| **Una única versión activa por familia** | **Implementado y Verificado** | Índice único `idx_versions_active_per_family` y lógica en `activate_version()`. |
| **Activación simultánea de documentos de familias diferentes** | **Implementado y Verificado** | `test_simultaneous_active_versions_across_families` pasando en `tests/test_etapa1_documental.py`. |
| **Sustitución transaccional de versiones activas** | **Implementado y Verificado** | Transacción inmediata `BEGIN IMMEDIATE` en `activate_version()`. |
| **Bloqueo de versiones inconsistentes, duplicadas y pendientes** | **Implementado y Verificado** | Bloqueo por `inconsistencia_identidad=True`, `status != PROCESADO` y `estado_revision != APROBADO`. |
| **Exclusión de categorías y familias desactivadas** | **Implementado y Verificado** | Filtro `(f.estado = 'ACTIVO' AND c.estado = 'ACTIVO')` en `get_active_versions()`, `get_active_version()`, `get_active_version_by_family()` y rechazo en `activate_version()`. |
| **Recuperación RAG sobre versiones autorizadas** | **Implementado y Verificado** | Filtro estricto `version_id IN authorized_version_ids` en `retriever.py` y abstención si conjunto vacío. |
| **Conservación del snapshot documental durante cada consulta** | **Implementado y Verificado** | Captura al inicio de `RAGService.query()` y persistencia inmutable en `authorized_versions_json` de `traces`. |
| **Protección de los endpoints administrativos** | **Implementado y Verificado** | Dependencia `verify_admin_key` en endpoints de `/api/admin`. |
| **Script de migración de Qdrant (`migrate_qdrant_payloads.py`)** | **Implementado y Verificado** | Pre-validación en memoria, configuración centralizada, cliente oficial `QdrantClient.set_payload(wait=True)`, dry-run, idempotencia verificada. |
| **Validador de correspondencia (`validate_qdrant_chunks.py`)** | **Implementado y Verificado** | Validador de solo lectura: correspondencia biunívoca, verificación de texto exacto, metadatos y ausencia de huérfanos. |
| **Pruebas automatizadas de migración y validación** | **Implementado y Verificado** | `tests/test_migrate_qdrant_payloads.py` (6 tests) y `tests/test_validate_qdrant_chunks.py` (5 tests). |
| **Migración real de payloads en el entorno host (Qdrant)** | **Implementado y Verificado** | 362/362 puntos actualizados en Qdrant con `family_id='fam_reglamento_tg'` y `categoria_id='cat_reglamentos'`. |
| **Índices de filtrado en Qdrant** | **Implementado y Verificado** | Índices KEYWORD creados en Qdrant para `version_id`, `family_id` y `categoria_id`. |
| **Pruebas automatizadas del backend (pytest)** | **Implementado y Verificado** | 104 pruebas pasando en 9.8s. |
| **Pruebas automatizadas del frontend (Vitest)** | **Implementado y Verificado** | 24 pruebas pasando en 1.9s. |
| **Compilación de producción frontend (tsc + vite build)** | **Implementado y Verificado** | `dist/` generado exitosamente sin advertencias de compilación. |
| **Etapa 2 (Evaluación RAG y métricas)** | **Pendiente de implementación** | No iniciada (por directriz explícita). |

---

## 3. Clasificación Estricta de Estado

### 3.1. Implementado y Verificado mediante Pruebas (Completado al 100%)
- Módulo `src/normativa/corpus/db.py`: soporte integral de categorías, familias y versiones con reglas de exclusión y bloqueo.
- Módulo `src/normativa/generation/rag_service.py`: snapshot inmutable de versiones autorizadas y trazabilidad forense.
- Módulo `src/normativa/retrieval/retriever.py` e `indexer.py`: filtros de Qdrant multi-versión y creación de índices keyword.
- Script `scripts/migrate_qdrant_payloads.py`: migración segura con pre-validación y dry-run.
- Script `scripts/validate_qdrant_chunks.py`: validador read-only de correspondencia exhaustiva.
- Suite `tests/` con 104 pruebas pasando (`pytest`).
- Suite `frontend/src/tests/` con 24 pruebas pasando (`vitest`).
- Build del frontend (`tsc && vite build`).

### 3.2. Ejecutado y Verificado en el Entorno Real del Host
- Creación de snapshot de seguridad en Qdrant: `normativa-2462940810676088-2026-11-27-18-15-19.snapshot`.
- Respaldo de seguridad de SQLite: `data/backups/normativa_pre_real_migration_20261127_131511.db`.
- Migración real de los 362 puntos en la colección `normativa` de Qdrant (`family_id`, `categoria_id`).
- Verificación de idempotencia (segunda corrida reporta 0 pendientes y 362 ya correctos).
- Creación de payload indexes KEYWORD en Qdrant para `version_id`, `family_id` y `categoria_id`.
- Validación de correspondencia 100% íntegra (0 discrepancias, 0 huérfanos, 0 faltantes, 100% texto coincidente).

### 3.3. Pendiente de Ejecutar en el Host
- **Ninguno para la Etapa 1**. Todo lo concerniente a la Etapa 1 se ejecutó y verificó en el host.

### 3.4. Pendiente de Implementación
- **Etapa 2**: Evaluación formal del motor RAG, dataset de preguntas y métricas de recuperación (Ragas/G-Eval).
- **Etapa 3, 4 y 5**: Posteriores fases del proyecto.

---

## 4. Conclusión

La **Etapa 1 (Gestión Documental y Versionamiento)** queda formalmente **AUDITADA, CORREGIDA, VERIFICADA Y CERRADA**.
