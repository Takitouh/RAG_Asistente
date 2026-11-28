# Flujo RAG y proveedor generativo

> Registro histórico de la implementación anterior a la corrección. Para el comportamiento y los resultados vigentes, consulte [Corrección arquitectónica de la Etapa 3](07_correccion_arquitectonica.md).

1. Snapshot de versiones activas aprobadas, procesadas y sin inconsistencias.
2. Embedding local BGE-M3 con filtro obligatorio por `version_id`.
3. Búsqueda léxica SQLite por términos, códigos F-DC/P-DC y artículos relacionados.
4. Fusión de candidatos explícitos, semánticos y léxicos; expansión jerárquica controlada.
5. Selección de máximo 12 chunks según modalidad y relevancia.
6. Generación mediante `LLMProvider`; Ollama conserva `qwen2.5:7b` como predeterminado.
7. Respuesta parcial/abstención/out-of-scope validada y citas reconstruidas desde metadatos autorizados.
8. Traza SQLite histórica.

El contrato expone `provider_name`, `model_name`, `complete`, timeout y compatibilidad con proveedor simulado. `LLM_PROVIDER`, `LLM_MODEL`, `OLLAMA_BASE_URL` son configurables.
