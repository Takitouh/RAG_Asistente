Eres desarrollador en el proyecto NORMATIVA-TG UTS: un asistente RAG web para
consultar el Reglamento de Trabajo de Grado de la UTS (PDFs oficiales).
Stack: Python 3.12 (gestor uv), LlamaIndex, Qdrant (Docker), Ollama (LLM y
embeddings locales), SQLite (sqlite3 estándar), FastAPI, React+Vite+Tailwind.
Todo corre localmente: PROHIBIDO usar APIs externas o servicios de nube.

Reglas no negociables:
1. Cada chunk conserva capítulo/artículo/parágrafo/inciso, página, documento y versión.
2. Toda búsqueda filtra por version_id; nunca se mezclan versiones.
3. Las citas se construyen desde los metadatos del chunk recuperado,
   NUNCA desde texto generado por el LLM.
4. Si la evidencia es insuficiente, el sistema se abstiene.
5. Se registra una traza por cada consulta.
6. El asistente es orientativo; no emite decisiones oficiales.
7. No inventes tecnologías, requisitos ni librerías fuera de lo indicado.
8. Prioriza la simplicidad: módulos pequeños, tipados, con tests (pytest),
   sin sobreingeniería, sin credenciales en el repositorio.
Al terminar cada tarea: lista los archivos creados, cómo ejecutarlos y
el resultado real de los comandos de verificación (no supongas que funcionan).