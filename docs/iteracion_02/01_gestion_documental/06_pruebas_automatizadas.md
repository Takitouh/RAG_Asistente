# Documentación de Pruebas Automatizadas — Etapa 1

Este documento compila el inventario real y los resultados de las suites de pruebas automatizadas del proyecto **NORMATIVA-TG UTS**.

---

## 1. Inventario Real de Suites de Pruebas

### 1.1. Backend (Python / pytest)

| Archivo de Prueba | Pruebas | Alcance y Objetivo |
| :--- | :---: | :--- |
| `tests/test_etapa1_documental.py` | 10 | CRUD de categorías y familias, detección de duplicados SHA-256, regla de activación única por familia, sustitución atómica, coexistencia multi-familia, bloqueo de versiones con discrepancia, exclusión de categorías/familias inactivas, inmutabilidad del snapshot en trazas, protección de endpoints admin. |
| `tests/test_migrate_qdrant_payloads.py` | 6 | Dry-run de migración Qdrant, escritura real de payloads (`family_id`, `categoria_id`), idempotencia, pre-validación con aborto ante huérfanos o desajustes de versión, manejo de errores de escritura. |
| `tests/test_validate_qdrant_chunks.py` | 5 | Validación exhaustiva SQLite <-> Qdrant: correspondencia biunívoca, detección de puntos huérfanos, detección de chunks sin punto, discrepancias de texto exacto, detección de metadatos faltantes. |
| `tests/test_rag_engine.py` | 30 | Motor RAG completo: generación con Qdrant y SQLite, citas bibliográficas basadas en metadatos, abstención ante falta de evidencia, detección de intenciones de cortesía, formato de respuesta orientativa. |
| `tests/test_rag_fixes.py` | 16 | Casos límite y correcciones de robustez del motor RAG, serialización JSON y gestión de dependencias. |
| `tests/test_corpus_management.py` | 12 | Endpoints administrativos de corpus, subida de documentos, endpoints de versión, informes de procesamiento. |
| `tests/test_ingestion_pipeline.py` | 10 | Pipeline de ingestión, extracción de PDFs, división por artículos/capítulos/parágrafos/incisos, cálculo de confianza OCR. |
| `tests/test_admin_auth_cookie.py` | 1 | Autenticación administrativa por cookies HTTP-only contra FastAPI. |
| `tests/test_api_v3_extensions.py` | 7 | Endpoints de extensión de API y utilidades del sistema. |
| `tests/test_health.py` | 1 | Verificación de estado de salud del backend (`/health`). |
| `tests/test_extractor.py` | 3 | Extracción de estructura legal en texto y regex normativo. |
| `tests/test_ollama_utils.py` | 3 | Conectividad y serialización con modelos locales de Ollama. |

**Total pruebas backend**: **104 pruebas** (100% pasando).

### 1.2. Frontend (TypeScript / Vitest / React Testing Library)

| Archivo de Prueba | Pruebas | Alcance y Objetivo |
| :--- | :---: | :--- |
| `frontend/src/tests/auth.test.tsx` | 10 | Login válido, login inválido, sesión persistente, prevención de bucles de redirección, logout seguro, protección frente a botón atrás, manejo de 401 y chat público sin auth. |
| `frontend/src/tests/chat.test.tsx` | 7 | Interfaz de chat público, renderizado de mensajes, visualización de citas, alertas de abstención y disclaimers. |
| `frontend/src/tests/admin.test.tsx` | 5 | Métricas administrativas, listado de versiones, botones de acción y estado del panel. |
| `frontend/src/tests/integration.test.tsx` | 2 | Flujos de integración de punta a punta entre chat y administración. |

**Total pruebas frontend**: **24 pruebas** (100% pasando).

---

## 2. Comandos de Ejecución

### 2.1. Backend
```bash
uv run pytest
```
*Salida esperada*: `104 passed, 1 warning in ~9s`.

### 2.2. Frontend
```bash
cd frontend
npm test -- --run
npm run build
```
*Salida esperada*: `4 passed (4), 24 passed (24)` y build exitoso (`dist/` generado).

### 2.3. Herramientas de Auditoría Qdrant
```bash
# Simulación sin escritura (dry-run):
uv run python scripts/migrate_qdrant_payloads.py --dry-run

# Validación de correspondencia (read-only):
uv run python scripts/validate_qdrant_chunks.py
```
