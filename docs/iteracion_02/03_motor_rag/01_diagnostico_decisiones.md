# Diagnóstico y decisiones de arquitectura

> Registro histórico de la implementación anterior a la corrección. Para el comportamiento y los resultados vigentes, consulte [Corrección arquitectónica de la Etapa 3](07_correccion_arquitectonica.md).

Estado confirmado: SQLite contiene 565 chunks y Qdrant 565 puntos; 384 chunks pertenecen a las 12 versiones activas. La consulta SQL y la validación biunívoca SQLite-Qdrant quedaron sin discrepancias.

Errores observados:
- Presentación: el backend recortaba el texto visible a 300 caracteres.
- Generación: el prompt exigía etiquetas internas y admitía respuesta mal fundamentada.
- Recuperación: la búsqueda léxica tenía extracción defectuosa de palabras clave y no privilegiaba códigos institucionales ni relaciones C1/C2.
- Citas: el modelo podía declarar identificadores, pero el backend ya descartaba IDs no recuperados; se eliminó la exposición pública del ID interno.
- Abstención: fuera de alcance se confundía con evidencia insuficiente.

Decisión: conservar Ollama y BGE-M3 localmente, añadir SQLite/LIKE y códigos institucionales como complementos, aplicar RRF simple por prioridad explícita/semántica/léxica y limitar el contexto seleccionado a 12 chunks. El proveedor quedó desacoplado mediante `LLMProvider`/`OllamaProvider` y un proveedor simulable.
