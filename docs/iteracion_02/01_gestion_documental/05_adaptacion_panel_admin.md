# Adaptación del Panel Administrativo — Etapa 1

Este documento detalla la implementación técnica del panel de administración del corpus documental en el backend (FastAPI) y frontend (React + TypeScript + Tailwind CSS).

---

## 1. Endpoints Administrativos de la API (`src/normativa/api/admin.py`)

Todos los endpoints administrativos están agrupados bajo `/api/admin` y protegidos por la dependencia `verify_admin_key`:

| Endpoint | Método | Descripción | Reglas y Validaciones |
| :--- | :--- | :--- | :--- |
| `/api/admin/login` | POST | Inicia sesión administrativa | Valida `admin_key` contra `settings.ADMIN_API_KEY`. Setea cookie HTTP-only `admin_session`. |
| `/api/admin/logout` | POST | Cierra sesión administrativa | Elimina la cookie `admin_session`. |
| `/api/admin/me` | GET | Estado de sesión | Retorna estado de autenticación y rol. |
| `/api/admin/stats` | GET | Métricas del corpus | Conteos de categorías, familias, versiones, chunks, trazas y versiones inconsistentes. |
| `/api/admin/categories` | GET | Listado de categorías | Parámetro `include_inactive=True/False`. |
| `/api/admin/categories` | POST | Crear categoría | Valida identificador y nombre únicos. |
| `/api/admin/categories/{id}` | GET/PUT/DELETE | Detalle, edición y borrado | Impide eliminar si existen familias asociadas (Regla 16). |
| `/api/admin/families` | GET | Listado de familias | Filtro opcional por `categoria_id`. |
| `/api/admin/families` | POST | Crear familia documental | Requiere `categoria_id`, `codigo`, `nombre`. |
| `/api/admin/families/{id}` | GET/PUT/DELETE | Detalle, edición y borrado | Impide eliminar si existen versiones asociadas (Regla 16). |
| `/api/admin/active-corpus` | GET | Corpus activo multi-documental | Retorna todas las versiones activas de familias y categorías activas. |
| `/api/admin/documents` | POST | Subida de PDFs | Detecta duplicados SHA-256 (`inconsistencia_identidad`). |
| `/api/admin/versions` | GET | Listado de versiones | Filtro opcional por `family_id`. |
| `/api/admin/versions/{id}` | GET | Detalle de versión | Incluye metadatos, informe de procesamiento y hashes. |
| `/api/admin/versions/{id}/activate` | POST | Activar versión | Transaccional (`BEGIN IMMEDIATE`). Desactiva la versión previa de la misma familia (Regla 7). Bloquea no procesados, rechazados, inconsistentes o bajo familia/categoría inactiva. |
| `/api/admin/versions/{id}/deactivate` | POST | Desactivar versión | Retira la versión del corpus activo sin destruirla. |
| `/api/admin/versions/{id}/review` | POST | Revisión documental | Acciones `approve` o `reject`. |
| `/api/admin/versions/{id}/metadata` | PATCH | Actualización de metadatos | Permite corregir vigencia, números de acuerdo y año. |

---

## 2. Endpoints Públicos (`src/normativa/api/admin.py` y `query.py`)

- `GET /api/versions/active`: Consulta pública del corpus activo y resumen de reglamentos habilitados.
- `GET /api/versions/{version_id}/pdf`: Descarga segura del documento PDF oficial dentro de `data/`.
- `POST /api/query`: Consulta RAG pública que aplica el snapshot de versiones activas autorizadas.

---

## 3. Seguridad y Control de Acceso

La función `verify_admin_key` soporta múltiples mecanismos estándar:
1. Cookie HTTP-only `admin_session` (utilizada por el frontend para navegación web fluida).
2. Header `X-Admin-Key` (para scripts y llamadas directas de consola).
3. Header `Authorization: Bearer <token>`.

Cualquier intento no autorizado devuelve `HTTP 401 Unauthorized`.

---

## 4. Componentes del Frontend (`frontend/src/`)

- `pages/AdminDashboardPage.tsx`: Vista principal protegida por `ProtectedRoute.tsx`.
- `components/admin/AdminDashboard.tsx`: Pestañas de control:
  - **Versiones**: Tabla de versiones con indicadores de estado de procesamiento, estado de revisión, vigencia institucional y botón de activación.
  - **Jerarquía**: Gestión y creación de categorías y familias documentales.
  - **Corpus Activo**: Visualización de los documentos que componen el corpus de respuesta RAG en tiempo real.
- `components/admin/DocumentUploadModal.tsx`: Modal para la carga de nuevos PDFs institucionales con selección de familia documental y campos normativos.
- `components/admin/VersionList.tsx`: Tabla detallada de versiones con alertas de discrepancia y opciones de revisión.
- `components/admin/MetadataEditModal.tsx` y `DocumentDetailModal.tsx`: Visualización y edición de metadatos.

---

## 5. Pruebas del Panel y Autenticación

- `frontend/src/tests/auth.test.tsx`: 10 pruebas de regresión de sesión administrativa, prevención de bucles de redirección, protección de rutas y logout.
- `frontend/src/tests/admin.test.tsx`: 5 pruebas de componentes administrativos, renderizado de estadísticas y listas de versiones.
- `frontend/src/tests/integration.test.tsx`: Flujo integrado de consulta en chat y gestión administrativa.
- `tests/test_admin_auth_cookie.py`: Verificación directa contra FastAPI de la autenticación mediante cookies HTTP-only.
