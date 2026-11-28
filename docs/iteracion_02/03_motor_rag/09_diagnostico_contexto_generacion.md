# Diagnóstico y optimización del contexto y la generación

## Línea base preservada

La intervención partió de `bd07d83` con 31 entradas en el estado de Git. Los cambios locales de las iteraciones previas seguían en el árbol de trabajo. El [estado inicial de Git](09_git_linea_base.txt), el [prompt exacto](09_prompt_linea_base.txt) y el [informe de calidad anterior](08_ajuste_calidad.md) registran esa línea base.

El proceso de diagnóstico cargó `Settings` antes de modificarlo. La solicitud real a Ollama confirmó el modelo Qwen2.5:7b y la [plantilla anterior](09_prompt_linea_base.txt) tiene SHA-256 `a45d723e0acd8cfeabc88c97b7bbac1ec9029da8a58ff87cc8ee0d0844462998`. Los parámetros efectivos fueron 6 candidatos por canal, hasta 6 candidatos iniciales del ranking combinado, 12 fragmentos enviados, expansión de las primeras 2 unidades sin tope independiente de fragmentos agregados, umbral semántico 0, ventana 10.240, reserva de 1.400 tokens de salida y 256 para la plantilla. El canal explícito de artículos se sumaba al ranking, así que el tamaño combinado podía superar el límite de un canal. Los dos errores sintéticos anteriores de premisa y respuesta parcial se conservaron como criterios estrictos.

## Presupuesto y seguridad

- Se reconstruye localmente la estimación BPE de Qwen2 con su vocabulario, fusiones y pretokenización. Ollama local entrega los datos mediante `/api/show` y se usa `tiktoken`, ya presente por LlamaIndex. Se cachea por URL y modelo. La app conserva la cota conservadora por bytes cuando los metadatos o el contador local no están disponibles.
- Se mide el contenido íntegro de ambos mensajes. Incluye instrucciones del sistema, pregunta, metadatos, marcas estructurales, referencias y texto de los fragmentos. En el modo Qwen2 se añade el esquema JSON como reserva, incluso cuando Ollama lo recibe por separado como gramática. Se mantienen otros 256 tokens para el envoltorio y 1.400 para la respuesta. La estimación de los mensajes por separado y su reserva anticipada se distinguen del recuento real de Ollama.
- El límite sigue siendo 10.240. Se verificó con `ollama ps` durante la matriz. Ollama 0.24.0 devolvió HTTP 400 con `truncate: false` al probar una entrada superior a una ventana deliberadamente pequeña. Se envía ese parámetro en cada consulta. El proveedor valida el recuento recibido y la finalización antes de publicar una respuesta. Si el servidor rechaza la entrada, se informa el error técnico y se conserva una sola llamada generativa.
- La política conserva el ranking semántico y léxico y el orden de expansión por versión. El tope opcional de añadidos se aplica a fragmentos que no estaban entre los candidatos iniciales. La traza identifica esos descartes y marca incompletas las unidades que pierden subdivisiones por el tope, cantidad o presupuesto.
- Los bytes miden la representación UTF-8. Los caracteres miden el texto Unicode. La estimación BPE cuenta unidades léxicas previstas y aplica reservas. Los tokens reales citados abajo son `prompt_eval_count` y `eval_count` que devuelve Ollama al terminar. El endpoint público `/api/tokenize` no estaba disponible en la instalación probada.

## Perfiles comparados

| Perfil | Prompt | TOP_K | Máximo enviado | Estimación | Máximo de añadidos |
| --- | --- | ---: | ---: | --- | --- |
| A | Anterior | 6 | 12 | Bytes | Sin tope propio |
| B | Anterior | 10 | 14 | BPE Qwen2 | 12 |
| C | Ajustado | 6 | 12 | Bytes | Sin tope propio |
| D | Ajustado | 10 | 14 | BPE Qwen2 | 12 |
| D5 / D15 | Ajustado | 5 / 15 | 14 | BPE Qwen2 | 12 |

El prompt ajustado conserva los campos JSON y explicita la dirección de mínimos y máximos, los puntos de inicio y vencimiento, las unidades temporales, el grupo y las excepciones. Pide cotejar hechos y pendientes con los fragmentos en la misma inferencia. Se mantuvo la temperatura en cero, el mismo modelo, las mismas preguntas y el mismo corpus sintético. Los casos son los cinco de la iteración anterior más plazos mínimos y máximos, una enumeración larga y una abstención sin respaldo. El barrido de 5/10/15 se centra en complemento, límites y enumeración larga. Para evitar que la carga alternada de los modelos distorsionara las comparaciones, se precalcularon los vectores BGE-M3 idénticos. El JSON registra el tiempo del embedding real por pregunta por separado de la recuperación y generación de cada ejecución.

## Uso del diagnóstico

El script usa las dos modalidades con el mismo generador. El diagnóstico RAG llama al retriever de producción. El manual localiza los identificadores del snapshot autorizado y utiliza el mismo filtro, selección, proveedor y citación. Conserva la traza en memoria para esta ejecución. El JSON incluye rankings, exclusiones, respuesta, citas y los mensajes exactos del envío a Ollama cuando se solicitó generación. `manual_context_complete` requiere todos los IDs y confirmación del proveedor. El código de salida 2 identifica una ejecución manual incompleta y el 1 un error técnico. La API pública sigue usando la recuperación automática.

```bash
uv run --no-sync python scripts/diagnosticar_rag.py listar --documento reglamento
uv run --no-sync python scripts/diagnosticar_rag.py listar --version VERSION_ID
uv run --no-sync python scripts/diagnosticar_rag.py listar --articulo NUMERO
uv run --no-sync python scripts/diagnosticar_rag.py listar --articulo NUMERO --paragrafo VALOR
uv run --no-sync python scripts/diagnosticar_rag.py listar --articulo NUMERO --literal LETRA
uv run --no-sync python scripts/diagnosticar_rag.py listar --documento DOCUMENTO --numeral 7.2
uv run --no-sync python scripts/diagnosticar_rag.py listar --documento DOCUMENTO --numeral 7.2 --actividad 3

uv run --no-sync python scripts/diagnosticar_rag.py --salida /tmp/rag-actual.json rag "Escriba aquí su pregunta"
uv run --no-sync python scripts/diagnosticar_rag.py --salida /tmp/rag-base.json rag "Escriba aquí su pregunta" --perfil base
uv run --no-sync python scripts/diagnosticar_rag.py --salida /tmp/rag-manual.json manual "Escriba aquí su pregunta" --chunk ID_1 --chunk ID_2
uv run --no-sync python scripts/diagnosticar_rag.py --salida /tmp/rag-top15.json rag "Escriba aquí su pregunta" --top-k 15 --max-contexto 14 --estimacion qwen2

PYTHONPATH=src:. uv run --no-sync python tests/run_etapa3_experiment.py --salida /tmp/rag-experimentos.json
```

Los valores en mayúsculas son marcadores de ejemplo. `--db` y `--salida` son opciones globales y van antes de la modalidad. `--prompt RUTA` permite usar un texto alternativo con cualquier perfil. Los overrides se aplican en el proceso del diagnóstico. El perfil base restablece los parámetros de la tabla y el prompt histórico. Cambiar `--ventana`, `--salida-tokens`, `--reserva-plantilla`, `--unidades-expansion`, `--max-expandidos` o `--min-score` permite probar límites adicionales sin editar la configuración permanente.

## Resultados y decisión

El [registro de las 48 ejecuciones](09_resultados_experimentos.json) contiene rankings y puntajes, candidatos iniciales, añadidos, descartes con motivo, IDs enviados, citas, contenido, estado, estimación, tokens reales y tiempos. Se redujeron los textos repetidos en este resumen. El comando de la matriz exporta las solicitudes y fragmentos completos.

La aprobación experimental exige el contenido solicitado, el estado esperado y las citas requeridas por el caso. En la consulta parcial, exige que cada pendiente corresponda al horario preguntado. Esta comprobación adicional complementa las pruebas previas sin cambiar sus criterios. La precisión de citas del registro es la proporción de IDs citados que corresponden a la evidencia esperada del caso. Es una medida sintética de pertinencia y debe complementarse con lectura de la respuesta.

| Perfil | Casos logrados | Mediana semánticos / léxicos / combinados | Iniciales / agregados / enviados | Tokens reales de entrada | Recuperación / generación / total |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 3/8 | 6 / 6 / 7 | 6 / 0,5 / 6 | 1.265 | 4,5 ms / 5,62 s / 5,63 s |
| B | 5/8 | 10 / 10 / 12,5 | 10 / 0 / 10 | 2.176 | 5,1 ms / 6,38 s / 6,57 s |
| C | 6/8 | 6 / 6 / 7 | 6 / 0,5 / 6 | 1.273 | 4,3 ms / 7,60 s / 7,61 s |
| D | 5/8 | 10 / 10 / 12,5 | 10 / 0 / 10 | 2.184 | 5,2 ms / 7,21 s / 7,22 s |
| D5 | 6/8 | 5 / 5 / 6 | 5 / 1 / 6 | 1.053 | 4,5 ms / 6,85 s / 6,85 s |

Los tiempos de la tabla excluyen la inferencia BGE-M3 precalculada. El archivo JSON conserva esa medición aparte. Las latencias de un banco aislado con caché no determinan la latencia pública. D repitió la respuesta de los dos casos compuestos y mantuvo los mismos resultados estrictos.

| TOP_K en el barrido | Complemento | Mínimo y máximo | Enumeración larga |
| --- | --- | --- | --- |
| 5 | Dos fuentes citadas | Ambas disposiciones citadas y unidades correctas | 13/13 con citas |
| 10 | Dos fuentes citadas | Valores y unidades correctos, faltó la cita del máximo | 13/13 con citas |
| 15 | Dos fuentes citadas | Faltó la cita del máximo | 11/13 en contexto tras exclusiones por cantidad |

| Enumeración larga | Caracteres | Bytes UTF-8 | Estimación de mensajes | Estimación con reservas | Tokens reales entrada / salida | Literales en contexto |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A | 7.892 | 8.040 | 8.040, cota por bytes | 8.296 | 1.843 / 94 | 4/13 |
| B | 20.072 | 20.499 | 4.591 | 5.002 | 4.604 / 171 | 13/13 |
| C | 7.845 | 7.993 | 7.993, cota por bytes | 8.249 | 1.851 / 144 | 4/13 |
| D / D5 | 20.025 | 20.452 | 4.599 | 5.010 | 4.612 / 206 | 13/13 |
| D15 | 18.391 | 18.781 | 4.271 | 4.682 | 4.284 / 196 | 11/13 |

A y C omitieron nueve literales por presupuesto. D5 envió el cuerpo y los trece literales. D15 omitió los literales l y m por el límite de 14 fragmentos al competir con otras coincidencias. En las 48 ejecuciones Ollama reportó `stop`. En los perfiles BPE, el recuento real superó al de los mensajes por 13 tokens en esta muestra, compatible con el envoltorio de chat. La reserva de 256 para la plantilla y 155 para el esquema absorbió ese desfase. El resultado observado no establece que el desfase siempre sea 13.

Se seleccionó **D5** con TOP_K 5, hasta 14 fragmentos, dos unidades ampliables, tope de 12 añadidos, BPE local y el prompt ajustado. Conserva la recuperación de todos los literales en la prueba de presión y el respaldo de ambas condiciones de plazo. C alcanzó el mismo puntaje estricto con una cobertura menor en la enumeración. Los ajustes viven en `.env.example` y en `Settings`. El SHA-256 del prompt elegido es `eef5c7abf6cd18232e36de4d389c000d5b571d7817b99c1e030042233af43a79`.

En modo manual, los dos fragmentos solicitados para la premisa ficticia llegaron a Ollama, con 730 tokens reales y código 0. El modelo corrigió ambos datos y volvió a dejar pendiente un dato ya respondido. Una segunda ejecución manual con un fragmento sobredimensionado en modo bytes devolvió código 2, `manual_context_complete: false` y `omitted_by_budget` para ese ID.

## Limitaciones

La prueba manual sitúa parte del problema en la interpretación y coherencia del modelo, incluso con evidencia completa y sin ruido de la búsqueda. En D5, la respuesta parcial del experimento identificó el horario y añadió como pendiente un dato de otro grupo. El control de IDs comprueba procedencia. La comprobación semántica por afirmación y la detección de omisiones siguen abiertas. La expansión conserva pertinencia local por unidad y depende de que el ranking encuentre documentos complementarios.

Una posible verificación selectiva mediante el mismo proveedor podría revisar respuestas parciales, premisas compuestas o listas con unidades incompletas. Revisaría correspondencia entre cada hecho, sus citas y los puntos pendientes. Qwen2.5 también podría equivocarse al verificar, y la segunda llamada añadiría tiempo de generación. Las medianas sintéticas variaron entre 5,62 y 7,60 s por generación en los perfiles completos. Es una hipótesis de coste, sujeta a medición y autorización posterior. La versión entregada realiza una sola inferencia. La validación normativa institucional queda para la evaluación independiente.

## Integridad y archivos

Se verificaron 565 registros y 565 puntos sin discrepancia, 384 chunks activos, 12 versiones activas y el contenido íntegro de las 245 trazas históricas. Los hashes de documentos, versiones, chunks, familias y categorías coincidieron al comienzo y al cierre.

| Área | Archivos de esta intervención |
| --- | --- |
| Configuración | `.env.example`, `src/normativa/config.py` |
| Generación | `src/normativa/generation/{generator,providers,rag_service,token_budget}.py` |
| Recuperación | `src/normativa/retrieval/{retriever,models,context_expander}.py` |
| Diagnóstico | `scripts/diagnosticar_rag.py` |
| Pruebas | `tests/test_etapa3_diagnostico.py`, `tests/run_etapa3_experiment.py`, `tests/{test_etapa3_calidad,test_etapa3_rag}.py` |
| Documentación | Este informe, `09_prompt_linea_base.txt`, `09_git_linea_base.txt` y `09_resultados_experimentos.json` |

## Verificaciones ejecutadas

| Comando | Resultado |
| --- | --- |
| `RUN_OLLAMA_INTEGRATION=0 uv run --no-sync pytest -q`, con copia temporal de SQLite | 174 aprobadas, 7 omitidas, 34,89 s |
| `RUN_OLLAMA_INTEGRATION=1 uv run --no-sync pytest -q --capture=tee-sys tests/test_etapa3_calidad.py tests/test_etapa3_rag.py -k 'real_ollama or generacion_real_ollama'` | 6 aprobadas, 1 fallida, 20 deseleccionadas, 78,30 s |
| `npm test`, desde `frontend` | 25 aprobadas en cuatro archivos |
| `npm run build`, desde `frontend` | Build de producción completado |
| `uv run --no-sync python scripts/validate_qdrant_chunks.py` | 565 puntos, 565 chunks, cero discrepancias |
| `git diff --check` | Sin errores |

La prueba previa de la premisa siguió fallando porque devolvió estado parcial tras corregir ambos hechos. La prueba previa de respuesta parcial pasó según su criterio original al mencionar el horario. El criterio adicional del experimento detectó que añadió un pendiente ajeno. La integración de activación de versiones y los controles de tokens aprobados mantienen sus comprobaciones previas.
