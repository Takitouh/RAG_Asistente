# Ajuste de calidad de la Etapa 3

## Diagnóstico comprobado

- En la línea base, una enumeración ficticia de siete literales llegó al modelo con cinco. La selección encontró el artículo y se quedó sin presupuesto de bytes antes de enviar dos fragmentos completos. Ollama respondió con cinco elementos y estado completo.
- Una consulta ficticia sobre dos grupos y una recomendación recibió una respuesta correcta en prosa, pero el modelo marcó como pendiente la recomendación que acababa de responder. Otra consulta dejó pendiente el acuse aun cuando el fragmento correspondiente estaba en el contexto. Ambos casos muestran límites de interpretación y cobertura, además del problema de recuperación.
- La expansión anterior colocaba todas las coincidencias iniciales antes de los fragmentos relacionados. Además, las actividades del procedimiento se identificaban por su número de actividad, que puede repetirse en distintos subnumerales. La ubicación almacenada permite identificar la sección correspondiente sin volver a procesar documentos.

## Ajustes

- La recuperación conserva la fusión existente. Para las dos unidades de mayor rango adelanta el contexto necesario del artículo o una actividad contigua del mismo subnumeral. En procedimientos solo se añaden actividades vecinas de la misma versión y sección. Las demás coincidencias iniciales conservan un lugar antes de las subdivisiones restantes.
- El contexto incluye la letra o marcador de los literales y avisa cuando parte de la misma unidad quedó fuera por cantidad o presupuesto. El prompt pide revisar cada dato solicitado, leer condiciones y excepciones junto con la regla y distinguir una recomendación de una obligación.
- La generación conserva estado, texto, referencias, motivo y una única lista de datos pendientes en lenguaje natural. La API mantiene los campos anteriores. Los pendientes se incorporan a la respuesta y siguen disponibles por separado para los clientes existentes. El chat evita mostrarlos dos veces.
- El modelo cita mediante referencias temporales. El backend las resuelve contra los fragmentos enviados y construye las citas desde SQLite. Las marcas parentéticas que correspondan a referencias válidas ya declaradas se retiran de la prosa. Una referencia inválida o una etiqueta técnica que persista provoca abstención segura.
- Las trazas nuevas registran los rankings por canal, la selección inicial, la expansión, las exclusiones por cantidad o presupuesto y el contexto enviado con su texto y referencias temporales. El proveedor registra los tokens de entrada y salida reportados por Ollama y el motivo de finalización. Los proveedores simulados quedan sin recuento real.

## Configuración

| Parámetro | Anterior | Actual |
| --- | ---: | ---: |
| `RAG_TOP_K` por canal y para la selección inicial | 5 | 6 |
| `RAG_MAX_CONTEXT_CHUNKS` | 10 | 12 |
| `RAG_CONTEXT_TOKENS` | 8.192 | 10.240 |
| Tokens reservados para la salida | 1.400 | 1.400 |
| Reserva conservadora de plantilla | 256 | 256 |

La cota de entrada actual es de 8.584 bytes UTF-8 para los contenidos de los mensajes de sistema y usuario, frente a 6.536 antes. Es una cota preventiva que mide el mensaje serializado, incluidos metadatos y texto íntegro de cada fragmento. Los caracteres cuentan unidades del texto Unicode, los bytes miden su codificación y los tokens provienen de Ollama. El proveedor rechaza finalizaciones por longitud y recuentos fuera de los límites establecidos. El experimento conserva la cota de bytes aunque el modelo use muchos menos tokens, porque el recuento real se recibe después de enviar la entrada.

## Método de comparación

Se usaron las mismas cinco consultas, los mismos fragmentos ficticios, BGE-M3, Qwen2.5:7b con temperatura cero, SQLite temporal y una colección Qdrant en memoria. Se capturaron las métricas directamente de la respuesta de Ollama tanto para la línea base como para la versión ajustada. En la versión actual la prueba verifica esos valores contra la traza. Ollama mostró una ventana activa de 10.240 tokens. Las latencias son observaciones de ejecuciones locales, sujetas al estado de carga y caché de los modelos.

El validador institucional confirmó 565 chunks, 565 puntos y cero discrepancias. La comparación de bases verificó igualdad de documentos, 13 versiones, 12 familias y 565 chunks. Permanecieron 384 chunks y 12 versiones activas. Las 232 trazas ya presentes se conservaron íntegramente. Durante la intervención el backend activo añadió una traza independiente.

## Resultados sintéticos

| Caso | Línea base | Versión ajustada |
| --- | --- | --- |
| Regla, excepción y recomendación | Aplicó los dos plazos correctos y también marcó la recomendación respondida como pendiente | Aplicó los dos plazos, distinguió lo recomendado de lo obligatorio y devolvió estado completo |
| Premisa compuesta incorrecta | Corrigió el plazo sin resolver la recomendación | Corrigió el plazo, omitió la recomendación y señaló como pendiente un dato ajeno a la consulta |
| Enumeración | Envió y citó cinco de siete literales | Envió el artículo y los siete literales y citó los siete |
| Fuentes complementarias | Respondió con el reglamento y dejó pendiente un dato que constaba en el procedimiento | Respondió con el registro y el acuse, con citas a ambas fuentes |
| Respuesta parcial | Respondió el plazo y marcó el horario como pendiente mediante una etiqueta técnica | Respondió el plazo, pero el pendiente se refirió a otro grupo y omitió el horario |

| Caso | Fragmentos antes → después | Caracteres antes → después | Bytes UTF-8 antes → después | Tokens de entrada antes → después | Tokens de salida antes → después | Tiempo total antes → después |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Condiciones | 6 → 7 | 3.211 → 4.603 | 3.236 → 4.657 | 905 → 1.241 | 148 → 103 | 10,27 → 7,87 s |
| Premisa | 6 → 6 | 3.192 → 3.794 | 3.215 → 3.823 | 902 → 1.029 | 158 → 120 | 12,88 → 10,92 s |
| Enumeración | 6 → 8 | 5.892 → 8.064 | 6.024 → 8.250 | 1.550 → 2.103 | 195 → 142 | 15,04 → 12,61 s |
| Complemento | 10 → 6 | 6.307 → 3.806 | 6.423 → 3.837 | 1.727 → 1.018 | 100 → 87 | 9,89 → 8,88 s |
| Parcial | 7 → 7 | 3.435 → 4.583 | 3.460 → 4.637 | 977 → 1.237 | 112 → 88 | 10,15 → 9,12 s |

Las cinco finalizaciones de la medición comparativa fueron `stop`. La prueba con contexto limitado a dos fragmentos registró seis exclusiones por cantidad y marcó la unidad como incompleta. Otra prueba registró la exclusión íntegra de un fragmento sobredimensionado por bytes y rechazó su cita.

## Límites

Los casos de premisa compuesta y consulta parcial son pruebas estrictas de Ollama real. Fallan si se omite una parte de la consulta o el modelo sustituye el dato pendiente por otro. Una referencia válida solo demuestra que el fragmento citado llegó al modelo. Sigue pendiente comprobar la correspondencia semántica por afirmación y la cobertura de cada subpregunta.

Una alternativa para evaluar sería una segunda inferencia con el mismo `LLMProvider` solo en consultas que presenten señales de cobertura incompleta. Podría contrastar cada afirmación y cada dato pendiente con la pregunta y el contexto original. Su beneficio, frecuencia y latencia requieren medición antes de incorporarla. La implementación actual usa una inferencia por consulta. La calidad normativa del corpus institucional queda para la evaluación independiente.

## Ejecución y archivos

- Backend completo con `uv run --no-sync pytest -q`.
- Calidad real con `RUN_OLLAMA_INTEGRATION=1 uv run --no-sync pytest -q --capture=tee-sys tests/test_etapa3_calidad.py`. Usa BGE-M3 y Qwen2.5:7b locales, SQLite temporal y Qdrant en memoria.
- Frontend desde `frontend`, `npm test` y `npm run build`.
- Correspondencia del corpus con `uv run --no-sync python scripts/validate_qdrant_chunks.py`.

| Verificación | Resultado observado |
| --- | --- |
| `uv run --no-sync pytest -q` con SQLite temporal | 171 aprobadas y 7 omisiones de las comprobaciones que requieren Ollama real |
| `RUN_OLLAMA_INTEGRATION=1 uv run --no-sync pytest -q --capture=tee-sys tests/test_etapa3_calidad.py` | 5 aprobadas y 2 fallidas en 54,75 s. Fallaron `premisa` y `parcial` |
| Integración existente de activación de versiones con Ollama | Aprobada durante la ejecución completa con inferencia real |
| `npm test` | 25 aprobadas en cuatro archivos |
| `npm run build` | Build de producción completado |
| `uv run --no-sync python scripts/validate_qdrant_chunks.py` | 565 chunks, 565 puntos y cero discrepancias |
| `git diff --check` | Sin errores |

Esta intervención modifica `.env.example`, `src/normativa/config.py`, `src/normativa/retrieval/{context_expander,models,retriever}.py`, `src/normativa/generation/{generator,providers,rag_service}.py`, `frontend/src/components/chat/ChatMessage.tsx`, `frontend/src/tests/chat.test.tsx` y `tests/{test_etapa3_rag,test_rag_engine,test_rag_fixes}.py`. Añade `tests/test_etapa3_calidad.py` y este informe. Se conservan los informes previos de la Etapa 3.
