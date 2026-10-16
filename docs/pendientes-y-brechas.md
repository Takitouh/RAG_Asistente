# Pendientes y brechas

Volver al [índice de documentación](README.md). Esta lista parte del
[estado actual](estado-actual.md) y de la [arquitectura actual](arquitectura-actual.md).

## Requisitos funcionales aún sin implementar

1. Definir y construir chunks a partir del documento parseado. Cada chunk debe
   llevar capítulo, artículo, parágrafo, inciso, página, documento y
   `version_id`.
2. Persistir documentos, versiones y trazas en SQLite usando la ruta ya
   configurada.
3. Crear la colección e insertar embeddings en Qdrant. Actualmente Qdrant está
   disponible, pero no hay colecciones.
4. Implementar recuperación con filtro obligatorio por `version_id`, sin mezclar
   versiones.
5. Implementar respuestas orientativas y abstención cuando la evidencia sea
   insuficiente.
6. Construir las citas exclusivamente con metadatos de los chunks recuperados;
   nunca con texto generado por el modelo.
7. Registrar una traza por cada consulta.
8. Exponer los endpoints necesarios para consulta e incorporar el frontend
   React/Vite/Tailwind previsto.

## Correcciones técnicas priorizadas

1. Resolver la prueba de regresión del PDF: falta el inciso `b` en el segundo
   parágrafo del artículo 15. La suite actual queda en 16/17.
2. Alinear la versión de Python: instrucciones del proyecto indican 3.12 y
   `pyproject.toml` exige 3.13.
3. Convertir los datos de parseo actuales en un contrato explícito de chunk y
   validar por pruebas que todos los metadatos obligatorios sobreviven al flujo
   de indexación y recuperación.
4. Añadir pruebas para filtro de versión, abstención, trazas y construcción de
   citas; hoy solo se prueban salud, extracción, parseo y comparación de
   modelos de Ollama.

## Límites actuales que deben mantenerse

- Todo el procesamiento y los modelos deben permanecer locales.
- El asistente no debe emitir decisiones oficiales.
- Las anomalías y reparaciones del OCR deben quedar visibles en los informes;
  no deben ocultarse como si fueran texto normativo confirmado.

Los comandos para validar cada avance están en
[Operación y verificación](operacion-y-verificacion.md).
