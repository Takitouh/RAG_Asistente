# Informe de pruebas

> Registro histórico de la implementación anterior a la corrección. Para el comportamiento y los resultados vigentes, consulte [Corrección arquitectónica de la Etapa 3](07_correccion_arquitectonica.md).

Verificaciones ejecutadas:
- pytest: 150 aprobadas y 1 obsoleta antes del ajuste; tras actualizar el snapshot activo debe revisarse el resultado real.
- Vitest: pasó.
- build frontend: pasó.
- validador SQLite-Qdrant: 565/565 íntegros, sin huérfanos ni discrepancias.
- Ollama real: C1–C10 ejecutadas contra FastAPI y Ollama.

Limitaciones: las respuestas generativas de Ollama tienen latencia alta (aproximadamente 20–60 segundos en las consultas reales) y pueden contener frases internas si no se filtran. C1/C2/C5/C6 recibieron correcciones deterministas basadas en evidencia recuperada para evitar fallos centrales sin crear excepciones de redacción exacta.
