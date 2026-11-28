# Estrategia de recuperación, citación y abstención

> Registro histórico de la implementación anterior a la corrección. Para el comportamiento y los resultados vigentes, consulte [Corrección arquitectónica de la Etapa 3](07_correccion_arquitectonica.md).

Recuperación: BGE-M3/Qdrant aporta similitud semántica; SQLite aporta coincidencia léxica, códigos institucionales y artículos/parágrafos. Las respuestas de formatos consultan P-DC-28/P-DC-29 y F-DC.

Citas: el backend solo crea citas para IDs presentes en los chunks seleccionados y versiones autorizadas. La API entrega el texto completo del fragmento. Los identificadores internos dejaron de mostrarse como texto público en la tarjeta.

Estados:
- completa: evidencia suficiente para todos los elementos respondidos;
- parcial: se da la evidencia disponible y se identifica el dato faltante;
- abstención por evidencia insuficiente: no existe respaldo recuperado suficiente;
- fuera de alcance: la consulta no pertenece al propósito académico, como matrícula/precios.

Limitación: una cita no demuestra por sí sola la pertinencia semántica; el control actual es de existencia, autorización y recuperación. Se recomienda validación académica posterior.
