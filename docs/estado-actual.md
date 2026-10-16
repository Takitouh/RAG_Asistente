# Estado actual

Volver al [índice de documentación](README.md).

## Resumen

El repositorio tiene una base de backend en Python para procesar el Reglamento
de Trabajo de Grado: extrae texto de un PDF, recurre a OCR cuando hace falta,
limpia ruido de página y separa el contenido en capítulos, artículos,
parágrafos e incisos. También expone una aplicación FastAPI mínima con el
endpoint `GET /health`.

La parte RAG todavía no está implementada: no hay carga de chunks en Qdrant,
búsqueda, generación de respuestas, construcción de citas, control de
`version_id`, traza de consultas ni interfaz React. Consulte el detalle en
[Pendientes y brechas](pendientes-y-brechas.md).

## Componentes disponibles

| Área | Estado | Evidencia |
| --- | --- | --- |
| API HTTP | Implementada de forma mínima | `GET /health` responde `{"status":"ok"}`. |
| Configuración local | Implementada | `Settings` lee `.env` y tiene valores por defecto en `src/normativa/config.py`. |
| Extracción PDF | Implementada | Usa capa de texto con `pdfplumber` u OCR en español con `pytesseract` y `pypdfium2`. |
| Limpieza | Implementada | Elimina encabezados/pies repetidos, índice y ruido, conservando líneas estructurales. |
| Parseo normativo | Implementado | Identifica capítulos, artículos, parágrafos, incisos, páginas, confianza OCR y anomalías. |
| Diagnóstico local | Implementado | `scripts/check_env.py` valida RAM/CPU, Qdrant, Ollama, embeddings y LLM. |
| Vectorización y recuperación | No implementada | No hay código que cree colecciones, inserte vectores ni consulte Qdrant. |
| Versionado y citas | No implementado | Los modelos de parseo no incluyen `version_id`, documento ni metadatos de cita completos. |
| Trazabilidad de consultas | No implementada | El paquete `tracing` está vacío. |
| Frontend | No presente | No hay proyecto React/Vite/Tailwind en el árbol actual. |

## Resultado documental disponible

El repositorio contiene el PDF de referencia y productos procesados ignorados
por Git bajo `data/`. El informe generado para ese PDF registra:

- 64 artículos de reglamento y 3 artículos de acuerdo.
- 16 capítulos, 36 parágrafos y 86 incisos.
- Una reparación del encabezado del artículo 1 por secuencia.
- Dos anomalías de capítulos fuera de secuencia, procedentes del OCR.

Los detalles del flujo y de los artefactos están en
[Arquitectura actual](arquitectura-actual.md). Los resultados de ejecución y
las limitaciones de prueba están en [Operación y verificación](operacion-y-verificacion.md).

## Compatibilidad observada

Aunque las instrucciones del proyecto indican Python 3.12, `pyproject.toml`
declara `>=3.13,<3.14` y la comprobación se ejecutó con Python 3.13.1. Esto es
una discrepancia de configuración que debe resolverse antes de fijar el entorno
objetivo.
