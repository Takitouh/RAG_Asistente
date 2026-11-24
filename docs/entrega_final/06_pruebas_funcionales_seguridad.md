# Verificación Funcional y Auditoría de Seguridad
## Informe de Ejecución de Pruebas Automatizadas y Evaluación de Seguridad
**Proyecto:** NORMATIVA-TG UTS (F-DC-124 / F-DC-125)  
**Institución:** Unidades Tecnológicas de Santander (UTS)  
**Fecha de ejecución:** Noviembre de 2026  
**Resultado Global:** 100% de Pruebas Pasadas (83 Backend / 24 Frontend)  

---

## 1. Resumen Ejecutivo de la Verificación

Se ejecutó la suite completa de aseguramiento de calidad sobre el repositorio local, comprendiendo pruebas unitarias, de integración, de regresión y de interfaz de usuario, tanto para el backend (Python / FastAPI) como para el frontend (TypeScript / React).

```text
================================================================================
RESUMEN GENERAL DE PRUEBAS AUTOMATIZADAS
================================================================================
Backend (Pytest 9.1.1, Python 3.12.3):    83 / 83 Pasadas (100% de éxito)
Frontend (Vitest 2.1.9, Node 18+):        24 / 24 Pasadas (100% de éxito)
Total de Pruebas Automatizadas:           107 Pruebas Ejecutadas y Aprobadas
Tiempo de Ejecución Backend:              5.32 segundos
Tiempo de Ejecución Frontend:             1.97 segundos
================================================================================
```

---

## 2. Detalle de Pruebas del Backend (Pytest)

Las 83 pruebas del backend evalúan de forma exhaustiva cada capa de la arquitectura, garantizando el cumplimiento de las reglas no negociables de negocio:

```text
tests/test_admin_auth_cookie.py .                                        [  1%]
tests/test_api_v3_extensions.py .......                                  [  9%]
tests/test_corpus_management.py ............                             [ 24%]
tests/test_extractor.py ...                                              [ 27%]
tests/test_health.py .                                                   [ 28%]
tests/test_ingestion_pipeline.py ..........                              [ 40%]
tests/test_ollama_utils.py ...                                           [ 44%]
tests/test_rag_engine.py ..............................                  [ 80%]
tests/test_rag_fixes.py ................                                 [100%]
======================== 83 passed, 4 warnings in 5.32s ========================
```

### 2.1. Desglose por Módulo de Backend
1. **`test_health.py` (1 prueba):**  
   Verifica la disponibilidad básica del servicio HTTP (`GET /health` devuelve `{"status":"ok"}`).
2. **`test_admin_auth_cookie.py` y `test_api_v3_extensions.py` (8 pruebas):**  
   Verifican la autenticación mediante cookies HttpOnly (`admin_session`), persistencia de sesión, conmutación de estado de vigencia, control de edición de metadatos normativos y prevención de accesos no autorizados (HTTP 401).
3. **`test_corpus_management.py` (12 pruebas):**  
   Evalúan el ciclo de vida del documento: carga de PDF, cálculo de hash SHA-256, registro de versión en SQLite, estados de procesamiento, aprobación humana y validación de seguridad de entrada.
4. **`test_extractor.py` e `test_ingestion_pipeline.py` (13 pruebas):**  
   Prueban la extracción digital directa (`pdfplumber`), el fallback automático a OCR (`pypdfium2` + `pytesseract`) ante PDFs escaneados, la limpieza posicional de encabezados/pies y el parseo estructural en capítulos, artículos, parágrafos e incisos.
5. **`test_rag_engine.py` (30 pruebas):**  
   Valida el flujo RAG de extremo a extremo: búsqueda en Qdrant con filtro de `version_id`, jerarquía de chunks, construcción determinista de citas, abstención ante evidencia nula, detección de saludos sociales y persistencia de trazas.
6. **`test_rag_fixes.py` (16 pruebas):**  
   Pruebas de regresión que confirman la corrección de defectos históricos: abstenciones falsas en preguntas legítimas, expansión jerárquica padre-hijo, soporte de preguntas ambiguas con aclaración (`clarification_needed: true`) y compatibilidad del contrato JSON con el frontend React.
7. **`test_ollama_utils.py` (3 pruebas):**  
   Comprueba la normalización de nombres de modelos en Ollama (`qwen2.5:7b`, `bge-m3:latest`) y la detección de dependencias locales ausentes.

---

## 3. Detalle de Pruebas del Frontend (Vitest)

Las 24 pruebas del frontend se ejecutan sobre un entorno simulado de DOM con `@testing-library/react` y `jsdom`:

```text
 RUN  v2.1.9 /home/jhon/PycharmProjects/FastAPIProject2/frontend

 ✓ src/tests/chat.test.tsx (7 pruebas)
 ✓ src/tests/admin.test.tsx (5 pruebas)
 ✓ src/tests/auth.test.tsx (10 pruebas)
 ✓ src/tests/integration.test.tsx (2 pruebas)

 Test Files  4 passed (4)
      Tests  24 passed (24)
   Duration  1.97s
```

### 3.1. Suites y Escenarios Evaluados en Frontend
- **Autenticación y Sesión Administrativa (`auth.test.tsx`):**
  1. Login válido: autentica contra FastAPI y redirige exactamente una vez al dashboard sin bucles.
  2. Login inválido: muestra mensaje de error y no permite el paso al dashboard.
  3. Sesión existente: permite entrar directamente a `/admin` sin pasar por login.
  4. Verificación inicial de sesión: muestra spinner de carga y no causa redirección prematura.
  5. Ausencia de bucles infinitos entre `/admin/login` y `/`.
  6. Logout controlado: invalida la cookie de sesión, limpia memoria y redirige inmediatamente al login.
  7. Protección contra botón Atrás: no permite reingresar al dashboard tras el logout.
  8. Sesión caducada: un error HTTP 401 en llamadas del panel desautentica de forma controlada.
  9. Tolerancia ante fallos de red: la pérdida de conectividad no genera navegación en bucle.
  10. Chat público: funciona libremente sin requerir autenticación alguna.
- **Interacción de Chat y Citas (`chat.test.tsx`):**  
  Envío de preguntas, renderizado de mensajes del usuario y del asistente, desglose de citas normativas, botón de expansión de fragmentos oficiales y manejo visual de estados de abstención.
- **Dashboard Administrativo (`admin.test.tsx`):**  
  Listado de versiones normativas, badges de estado de procesamiento (`PROCESADO`, `REVISION_PENDIENTE`), modal de carga de nuevo archivo PDF, modal de auditoría OCR y botón de activación de versión con un solo clic.
- **Integración de Contratos (`integration.test.tsx`):**  
  Verificación de visualización del disclaimer orientativo obligatorio del **F-DC-124** y persistencia del historial de conversación en el cliente.

---

## 4. Auditoría de Seguridad Técnica

### 4.1. Análisis de Exposición de Credenciales
- **Inspección de código fuente y control de versiones:**  
  Se realizó un escaneo recursivo en el repositorio Git (`.git/`, `src/`, `frontend/src/`) en búsqueda de tokens, contraseñas en duro o llaves privadas.
- **Resultado:** No existen credenciales embebidas en el código.
- **Variables de Entorno:** Todas las configuraciones sensibles se leen a través de `Settings` (`src/normativa/config.py`) mediante `pydantic-settings`.
- **Protección Git:** El archivo `.env` se encuentra declarado en `.gitignore`. Se provee únicamente `.env.example` con valores predeterminados para desarrollo local (`ADMIN_API_KEY=dev-admin-secret-key`).

### 4.2. Protección contra Directory Traversal (Recorrido de Directorios)
El sistema expone un visor del documento PDF original para que el estudiante o docente contraste la cita. Se comprobó la defensa implementada en `src/normativa/api/admin.py`:
- El endpoint toma el `version_id`, localiza el documento en SQLite y resuelve la ruta absoluta con `.resolve()`.
- Se evalúa `target_path.is_relative_to(allowed_dir)`.
- **Prueba de inyección de ruta:** Se intentaron solicitudes con cargas útiles como `../../etc/passwd` y `%2e%2e%2f`. En todos los casos el servidor rechazó la solicitud con código `HTTP 403 Forbidden` o `404 Not Found`.

### 4.3. Prevención de Inyección SQL (SQLi)
- Todas las consultas a SQLite en `src/normativa/corpus/db.py` y `src/normativa/tracing/db.py` emplean consultas parametrizadas estándar (`cursor.execute("SELECT ... WHERE id = ?", (id,))`).
- Ninguna cadena de entrada del usuario o del administrador se concatena directamente en sentencias SQL.

### 4.4. Protección CSRF y Cookies Seguras
- La cookie `admin_session` se genera con el atributo `SameSite="lax"`, impidiendo que peticiones forjadas desde sitios web externos transmitan la credencial administrativa.
- Para despliegues en producción sobre HTTPS, el flag `secure=True` puede activarse directamente en la configuración de la cookie.

### 4.5. Validación y Sanitización de Archivos Subidos
- El formulario de carga de documentos verifica que la extensión sea estrictamente `.pdf` y que el tamaño binario sea mayor a 0 bytes.
- Se calcula de forma inmediata el hash criptográfico SHA-256 para prevenir colisiones o adulteraciones accidentales del corpus normativo.

---

## 5. Matriz de Comprobación de Flujos del Sistema

| Flujo Evaluado | Estado Operativo | Evidencia Registrada |
| :--- | :---: | :--- |
| **Consulta Normativa RAG** | **Conforme** | Endpoint `/api/query` responde con respuesta estructurada, citas y disclaimer. |
| **Presentación de Citas** | **Conforme** | Citas desglosadas con capítulo, artículo, parágrafo, inciso y página física. |
| **Visualización de PDF** | **Conforme** | Visualización de página en PDF original confinado en `data/pdfs/`. |
| **Mecanismo de Abstención** | **Conforme** | Activación de `abstained: true` ante consultas fuera de alcance o sin datos. |
| **Login / Logout Admin** | **Conforme** | Emisión y destrucción de cookie HttpOnly sin bucles de redirección. |
| **Protección de Rutas** | **Conforme** | Rutas `/admin/*` inaccesibles sin autenticación válida (HTTP 401). |
| **Ingestión e Indexación** | **Conforme** | Pipeline extrae texto, limpia ruido e inserta vectores en Qdrant. |
| **Auditoría OCR** | **Conforme** | Inspección de confianza por página, líneas eliminadas y anomalías. |
| **Activación de Versiones** | **Conforme** | Conmutación instantánea de versión activa en SQLite y Qdrant. |
| **Persistencia de Trazas** | **Conforme** | Registro completo de cada interacción en la tabla `traces` de SQLite. |

---
*Fin del Documento 06 — Verificación Funcional y Auditoría de Seguridad.*
