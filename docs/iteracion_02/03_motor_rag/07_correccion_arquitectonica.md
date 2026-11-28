# Corrección arquitectónica de la Etapa 3

## Cambios en producción

- `RAGService.query` dejó de clasificar el alcance por palabras clave, responder por su cuenta sobre evaluadores o formatos y reemplazar salidas sobre plazos o sustentaciones. El servicio usa el proveedor para toda respuesta sustantiva.
- `NormativeRetriever.retrieve` dejó de asociar temas a artículos, excluir fuentes por modalidad o reordenar artículos concretos. `_lexical_search` eliminó el vocabulario normativo preseleccionado y busca términos e identificadores de cualquier consulta. `expand_normative_context` aplica la misma expansión a todos los artículos recuperados.
- `NormativeGenerator.generate` eliminó la detección de abstención por prefijo, la identificación de aclaraciones con expresiones regulares y la asignación automática de citas por artículo o puntuación. La detección social conserva únicamente patrones acotados de cortesía.
- La revisión del flujo de producción abarcó el servicio, generador y prompt, citas, intenciones, proveedores, recuperación y ruta pública. Las respuestas sustantivas provienen de la generación con el contexto recuperado. Las únicas salidas directas cubren cortesía, carencia de evidencia, salida inválida y fallos técnicos. Los archivos de evaluación y los informes previos se conservan como registros históricos.

## Flujo vigente

1. FastAPI captura las versiones activas, procesadas, aprobadas y sin discrepancias de identidad. Cada consulta a Qdrant y cada lectura de chunks en SQLite se limitan a ese conjunto. La activación sigue siendo transaccional y está limitada a una versión por familia.
2. BGE-M3 genera el vector para Qdrant. SQLite aporta un ranking por coincidencias de términos normalizados e identificadores documentales, además de las referencias explícitas a artículos o capítulos. Si se solicita un inciso o parágrafo del artículo, la búsqueda lo presenta primero. La fusión prioriza referencias explícitas y alterna las dos listas de pertinencia, eliminando repetidos por ID. Cada lista mantiene su orden y se evitan comparaciones entre puntuaciones de distinta escala.
3. La expansión de los primeros candidatos aporta cuerpo, incisos y parágrafos del mismo artículo y versión. El backend verifica en SQLite que cada candidato exista, pertenezca al documento de la versión y tenga un rango de páginas coherente. Cuando el informe incluye el número de páginas, también verifica el extremo superior. El generador selecciona hasta diez fragmentos completos según el orden de recuperación y el presupuesto restante.
4. El proveedor recibe consulta y fragmentos como datos JSON, separados del mensaje de sistema. El perfil documental acompaña cada fragmento. El prompt usa reglamentos para reglas generales, procedimientos para su operación y formatos para campos y requisitos de la plantilla. Las condiciones y modalidades deben sustentarse en el texto recuperado. Cualquiera de estos tipos puede aportar evidencia pertinente.
5. `LLMProvider` recibe un esquema Pydantic convertido a JSON Schema. `LLM_PROVIDER=ollama` selecciona Qwen2.5:7b local por defecto y `LLM_TIMEOUT_SECONDS` configura el tiempo de espera. `LLM_PROVIDER=simulated` permite pruebas sin inferencia. Se puede inyectar una implementación del contrato al construir `RAGService`.
6. La API devuelve `complete`, `partial`, `insufficient_evidence`, `out_of_scope`, `technical_error` o `social`. Entrega el texto, las partes cubiertas y pendientes, el motivo de abstención y las citas usadas. Las respuestas parciales conservan su contenido sustentado. Un fallo técnico tiene estado HTTP 503.
7. Las citas se reconstruyen exclusivamente desde los metadatos canónicos de los fragmentos enviados al modelo. Si el JSON es inválido o el modelo incluye un ID fuera del contexto, se aplica abstención segura. Se entrega el fragmento íntegro y se conserva el acceso al PDF por versión.
8. Cada consulta válida genera una traza con snapshot, ranking de candidatos, contexto enviado, citas usadas, proveedor, modelo, resultado y duraciones de embedding, recuperación semántica y léxica, selección, inferencia, validación y total. La migración de `diagnostics_json` es aditiva.

Ollama recibe una ventana explícita de 8.192 tokens y un máximo de 1.400 tokens de salida. Durante la prueba, `ollama ps` mostró una ventana activa de 8.192 y `ollama show` informó una capacidad de 32.768 para el modelo local. El presupuesto de entrada se calcula sobre el mensaje serializado en bytes UTF-8 con reserva para la plantilla. Se omiten unidades completas que no caben y se rechaza una generación cortada o que exceda el recuento permitido de entrada. El límite puede reducir cobertura en consultas que requieran muchas unidades. La verificación de identificadores y metadatos comprueba procedencia, mientras que comprobar el respaldo semántico de cada afirmación requiere evaluación independiente.

## Administración y preservación

Se conservan el conteo dinámico de fragmentos activos, los bloqueos de activación, la evidencia completa y la gestión documental. La migración corrigió los rótulos históricos de F-AM-04 y F-DC-126, 127, 128, 129, 130 y 196. La comparación de filas antes y después confirmó igualdad de los documentos, versiones, chunks y contenido de las 213 trazas históricas. Se conservaron 13 versiones, 12 familias, 12 versiones activas y 384 chunks activos. La validación de correspondencia confirmó 565 registros en SQLite, 565 puntos en Qdrant y cero discrepancias. Los 12 PDF activos estaban disponibles en disco y el contrato administrativo devolvió los nombres corregidos.

## Ejecución local

- API con `uv run --no-sync uvicorn normativa.api.main:app` y frontend de desarrollo con `cd frontend && npm run dev`.
- Suite con `uv run --no-sync pytest -q`. Las pruebas previas de correspondencia esperan acceso a Qdrant local y al snapshot institucional de SQLite. Para la verificación se usó una copia de SQLite y un directorio temporal para los archivos de prueba.
- Generación real con `RUN_OLLAMA_INTEGRATION=1 uv run --no-sync pytest -q tests/test_etapa3_rag.py -k generacion_real_ollama`. Usa SQLite temporal y Qdrant en memoria, además de BGE-M3 y Qwen2.5:7b locales.
- Frontend con `cd frontend && npm test` y `npm run build`.
- Corpus con `uv run --no-sync python scripts/validate_qdrant_chunks.py`.

La prueba real verificó dos activaciones del corpus sintético y el cambio en la respuesta y en el artículo citado. Los dobles de prueba comprueban que el servicio use el proveedor, preserve respuestas parciales, separe los tipos de abstención y error, rechace citas inválidas, y registre tiempos y contexto. La calidad normativa del corpus institucional queda pendiente de la evaluación independiente.

## Resultados de verificación

| Comando | Resultado |
| --- | --- |
| `RUN_OLLAMA_INTEGRATION=1 uv run --no-sync pytest -q -o faulthandler_timeout=75` | 167 aprobadas en 50,22 s con la integración real habilitada. El aviso corresponde a la deprecación de HTTPX en Starlette TestClient. |
| `npm test` | 24 aprobadas en cuatro archivos. Vitest mostró avisos de React Router. |
| `npm run build` | Build de producción completado. |
| `uv run --no-sync python scripts/validate_qdrant_chunks.py` | 565 chunks, 565 puntos, cero discrepancias. |
| `git diff --check` | Sin errores de formato del diff. |

## Archivos de esta corrección

| Área | Archivos |
| --- | --- |
| Generación | `src/normativa/generation/{rag_service,generator,providers,citations,intents}.py` |
| Recuperación | `src/normativa/retrieval/{retriever,explicit_matcher,context_expander,models}.py` |
| API, configuración y persistencia | `src/normativa/api/{admin,query}.py`, `src/normativa/config.py`, `.env.example`, `src/normativa/corpus/db.py`, `src/normativa/tracing/{db,models}.py` |
| Frontend | `frontend/src/{api/client,hooks/useChat,types/index}.ts`, `frontend/src/components/chat/{ChatMessage,AbstentionAlert}.tsx`. Conservados los cambios locales de `AdminDashboard`, `VersionList` y `CitationCard`. |
| Pruebas | Nuevo `tests/test_etapa3_rag.py`. Adaptados al contrato `tests/test_rag_engine.py` y `tests/test_rag_fixes.py`. Conservado el cambio local de `tests/test_etapa2_procesamiento.py`. |
| Documentación | Nuevo informe `07_correccion_arquitectonica.md`. Rotulados como históricos los informes `01_diagnostico_decisiones.md`, `02_flujo_rag_proveedor.md`, `03_estrategia_citas_abstencion.md` y `06_informe_pruebas.md`. |
