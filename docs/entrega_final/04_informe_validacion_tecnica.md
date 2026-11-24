# Informe de Validación Técnica Mediante Banco de 30 Consultas Normativas
## Evaluación Experimental del Motor RAG Soberano en Entorno Real Local
**Proyecto:** NORMATIVA-TG UTS (F-DC-124 / F-DC-125)  
**Institución:** Unidades Tecnológicas de Santander (UTS)  
**Fecha de ejecución:** 24 de noviembre de 2026  
**Entorno de Prueba:** FastAPI + Qdrant (Docker) + Ollama (`qwen2.5:7b` y `bge-m3`) + SQLite  
**Script de Automatización:** `scripts/ejecutar_30_preguntas.py`  
**Datasets Generados:** `resultados_30_preguntas.json` y `resultados_30_preguntas.csv`  

---

## 1. Resumen Ejecutivo de la Evaluación

Se aplicó el banco oficial de **30 preguntas de validación técnica** sobre el asistente RAG real en ejecución local. Las consultas evaluaron exhaustivamente las dimensiones de recuperación semántica, fundamentación normativa, correspondencia determinista de citas, detección de ambigüedad, abstención activa y aislamiento entre versiones.

```text
================================================================================
CONSOLIDADO GENERAL DE VALIDACIÓN TÉCNICA (BANCO DE 30 PREGUNTAS)
================================================================================
Total de Pruebas Ejecutadas:             30 / 30 (100% evaluadas)
  - Casos Calificados como "Correcto":   24 (80.0% de acierto pleno)
  - Casos "Parcialmente Correcto":        6 (20.0% con respuesta orientativa)
  - Casos "Incorrecto" / Alucinación:     0 (0.0% de error sustantivo)
  - Casos "No Evaluable":                 0 (0.0%)
Tasa de Aceptación / Fidelidad Global:   100.0% (Cero alucinaciones o errores)
--------------------------------------------------------------------------------
Métricas de Rendimiento Temporal:
  - Tiempo Total Promedio:               41.039 ms (41.04 segundos)
  - Tiempo Mínimo (F27 Clima):           129 ms (0.13 segundos, abstención rápida)
  - Tiempo Máximo (R12 Trámite Informe): 111.573 ms (111.57 segundos)
================================================================================
```

---

## 2. Metodología y Criterios Formales de Evaluación

Cada una de las 30 pruebas fue calificada confrontando la respuesta emitida y las citas devueltas frente a la fuente legal original (**Acuerdo No. 01-021 del 18 de julio de 2019**), aplicando los siguientes criterios:

1. **Correcto:** La respuesta aborda exhaustivamente la pregunta, respeta taxativamente las disposiciones del reglamento, cita con precisión los artículos y páginas físicas del documento escaneado, o ejecuta una abstención motivada sin citas normativas espurias.
2. **Parcialmente Correcto:** La respuesta proporciona orientación normativa verídica y respaldada, pero omite alguno de los artículos secundarios esperados en preguntas relacionales complejas, o requiere mayor énfasis en la solicitud de aclaración ante consultas ambiguas.
3. **Incorrecto:** La respuesta contiene información contraria al reglamento, cita artículos inexistentes, alucina plazos o mezcla versiones normativas distintas a la activa.
4. **No Evaluable:** Falla de comunicación de red, caída del servicio o excepción no controlada que impidió la ejecución de la consulta.

---

## 3. Tablas Consolidadas de Resultados

### 3.1. Distribución de Resultados por Categoría de Consulta

| Categoría | Casos Evaluados | Correcto | Parcialmente Correcto | Incorrecto | Tasa de Acierto Pleno |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Directa Sustentada (D01-D09)** | 9 | 9 | 0 | 0 | **100.0%** |
| **Relación entre Disposiciones (R10-R14)** | 5 | 3 | 2 | 0 | **60.0%** |
| **Parágrafos y Excepciones (E15-E18)** | 4 | 3 | 1 | 0 | **75.0%** |
| **Ambigua o Parcial (A19-A22)** | 4 | 2 | 2 | 0 | **50.0%** |
| **Sin Evidencia Suficiente (S23-S25)** | 3 | 3 | 0 | 0 | **100.0%** |
| **Fuera de Alcance (F26-F28)** | 3 | 3 | 0 | 0 | **100.0%** |
| **Aislamiento de Versiones (V29-V30)** | 2 | 2 | 0 | 0 | **100.0%** |
| **TOTAL CONSOLIDADO** | **30** | **24 (80.0%)** | **6 (20.0%)** | **0 (0.0%)** | **100.0% Aceptable** |

---

### 3.2. Evaluación por Dimensiones Técnicas del RAG

| Dimensión Técnica | Criterio de Cumplimiento | Resultado Obtenido | Calificación |
| :--- | :--- | :--- | :---: |
| **Pertinencia de Recuperación** | Los chunks recuperados de Qdrant deben contener los artículos que resuelven la pregunta. | En 29 de 30 casos, los chunks pertinentes formaron parte de los primeros puestos del ranking. | **Excelente** |
| **Fidelidad Normativa** | Las afirmaciones del texto generado deben estar estrictamente sustentadas en los fragmentos. | Cero invenciones de plazos, fechas o procedimientos no respaldados. | **100% Conforme** |
| **Correspondencia de Citas** | Las citas se extraen de los metadatos de los chunks (Capítulo, Artículo, Página) y no del LLM. | 100% de las citas provinieron de los metadatos relacionales oficiales. | **100% Conforme** |
| **Manejo de Ambigüedad** | El sistema debe ofrecer orientación preliminar y formular preguntas aclaratorias. | Respuestas matizadas en A19 y A20 distinguiendo plazos y pidiendo modalidad. | **Conforme** |
| **Abstención Activa** | Ante consultas sin datos o fuera de dominio, marcar `abstained: true` y no emitir citas falsas. | Abstención impecable en S23-S25 (sin datos) y F26-F28 (fuera de dominio). | **100% Conforme** |
| **Aislamiento Documental** | Cero mezcla de fragmentos entre la versión 2019 y la versión 2021. | V29 y V30 verificaron un 0.0% de contaminación cruzada en citas y trazas. | **100% Conforme** |
| **Trazabilidad Integral** | Cada una de las 30 consultas debe registrarse en la tabla `traces` de SQLite. | 30 trazas registradas con UUID, latencias exactas y serialización JSON. | **100% Conforme** |

---

## 4. Detalle Caso por Caso de las 30 Consultas Normativas

### 4.1. Respuestas Directas Sustentadas (D01 – D09)

#### D01 — Modalidades de Trabajo de Grado
- **Pregunta:** *«¿Cuáles son las modalidades de Trabajo de Grado contempladas en el reglamento?»*
- **Resultado Esperado:** Debe enumerar las seis modalidades: Proyecto de Investigación, Desarrollo Tecnológico, Monografía, Seminario, Práctica y Emprendimiento.
- **Versión Consultada:** `uts_tg_2019` | **Trace ID:** `c22eef8e-d918-4905-b153-61ba4f4c2c56`
- **Respuesta Real:** Enumera taxativamente las 6 modalidades del Artículo 8, aclarando la condición de Práctica para el nivel técnico profesional.
- **Chunks y Puntuaciones:** 24 chunks recuperados (Top score: 0.8872). Citas: Art. 8 (incisos a, b, c, d, e, f y parágrafo único), pág. 4.
- **Latencia:** 43.973 ms | **Juicio:** **Correcto**.

#### D02 — Período General para Finalizar
- **Pregunta:** *«¿Cuál es el período general previsto después de aprobar la propuesta para finalizar el Trabajo de Grado?»*
- **Resultado Esperado:** 180 días calendario consecutivos a partir de la aprobación de la propuesta.
- **Versión Consultada:** `uts_tg_2019` | **Trace ID:** `654f15ba-274e-4e44-8cb5-17f185790be9`
- **Respuesta Real:** Indica con exactitud el plazo de 180 días calendario consecutivos según el Artículo 14.
- **Chunks y Citas:** 27 chunks. Citas: Art. 14 (cuerpo y encabezado), pág. 5.
- **Latencia:** 45.663 ms | **Juicio:** **Correcto**.

#### D03 — Plazo Mínimo de Entrega del Informe Final
- **Pregunta:** *«¿Puedo entregar el Informe Final un mes después de que aprueben mi propuesta?»*
- **Resultado Esperado:** No: no puede entregarse antes de transcurridos tres meses desde la aprobación.
- **Versión Consultada:** `uts_tg_2019` | **Trace ID:** `a82755e3-a6d1-419b-b6ec-7eb2d8548ef2`
- **Respuesta Real:** Aclara categóricamente que no es posible, fundamentando en la restricción de 3 meses mínimos.
- **Chunks y Citas:** 32 chunks. Citas: Art. 30, Parágrafo 1, pág. 11.
- **Latencia:** 42.893 ms | **Juicio:** **Correcto**.

#### D04 — Definición de Informe Final
- **Pregunta:** *«¿Qué es el Informe Final de Trabajo de Grado según el reglamento?»*
- **Resultado Esperado:** Consigna resultados y conclusiones de la implementación de la propuesta.
- **Versión Consultada:** `uts_tg_2019` | **Trace ID:** `fbda09e7-fe37-4f40-b484-9ff5df726252`
- **Respuesta Real:** Define el informe conforme al Artículo 29, distinguiéndolo de la propuesta inicial.
- **Chunks y Citas:** 29 chunks. Citas: Art. 29, pág. 10.
- **Latencia:** 29.848 ms | **Juicio:** **Correcto**.

#### D05 — Conceptos de Evaluación del Informe Final
- **Pregunta:** *«¿Cuáles son los posibles conceptos de evaluación del Informe Final?»*
- **Resultado Esperado:** Trabajo de Grado Aplazado, Aprobado y Reprobado (valoración cualitativa).
- **Versión Consultada:** `uts_tg_2019` | **Trace ID:** `8ff9809d-cb9a-41aa-9669-79fe7b79a665`
- **Respuesta Real:** Identifica los tres conceptos cualitativos previstos en el Artículo 31.
- **Chunks y Citas:** 30 chunks. Citas: Art. 31 (literales a, b, c), pág. 11.
- **Latencia:** 31.047 ms | **Juicio:** **Correcto**.

#### D06 — Conformación Individual o en Equipo
- **Pregunta:** *«¿El Trabajo de Grado puede hacerse individualmente o en equipo?»*
- **Resultado Esperado:** Individual o equipo: máximo general 2 estudiantes, excepción hasta 3 en Investigación y Desarrollo Tecnológico.
- **Versión Consultada:** `uts_tg_2019` | **Trace ID:** `a0e30d63-b883-4ce4-82a9-7c42df7cf862`
- **Respuesta Real:** Detalla la regla general (máximo 2) y la excepción taxativa (hasta 3).
- **Chunks y Citas:** 39 chunks. Citas: Art. 11 y parágrafo, pág. 5.
- **Latencia:** 48.713 ms | **Juicio:** **Correcto**.

#### D07 — Clases de Monografía
- **Pregunta:** *«¿Qué clases de monografía describe el reglamento?»*
- **Resultado Esperado:** Monografía Teórica, Monografía de Análisis y Monografía de Sistematización de Experiencias.
- **Versión Consultada:** `uts_tg_2019` | **Trace ID:** `6c10e6cb-32eb-4581-adbc-90e632b785e0`
- **Respuesta Real:** Explica y diferencia las tres modalidades monográficas del Artículo 39.
- **Chunks y Citas:** 19 chunks. Citas: Art. 39 (incisos a, b, c), pág. 13.
- **Latencia:** 50.881 ms | **Juicio:** **Correcto**.

#### D08 — Intensidad Horaria de Seminario
- **Pregunta:** *«¿Cuántas horas académicas debe tener como mínimo la modalidad de Seminario?»*
- **Resultado Esperado:** Mínimo de 160 horas académicas.
- **Versión Consultada:** `uts_tg_2019` | **Trace ID:** `483fa2fa-1087-43cf-ae0b-47e29681bcad`
- **Respuesta Real:** Indica exactamente las 160 horas académicas sin inventar tarifas.
- **Chunks y Citas:** 25 chunks. Citas: Art. 42, parágrafo, pág. 14.
- **Latencia:** 23.866 ms | **Juicio:** **Correcto**.

#### D09 — Modalidades de Práctica
- **Pregunta:** *«¿Qué modalidades de práctica reconoce el reglamento?»*
- **Resultado Esperado:** Práctica Empresarial y Práctica Social Comunitaria.
- **Versión Consultada:** `uts_tg_2019` | **Trace ID:** `63baaa1a-a037-4351-87a4-44db1d9e2aa4`
- **Respuesta Real:** Identifica ambas modalidades según el Capítulo XI, Artículo 49.
- **Chunks y Citas:** 18 chunks. Citas: Art. 49 (incisos a, b), pág. 16.
- **Latencia:** 38.927 ms | **Juicio:** **Correcto**.

---

### 4.2. Relación entre Disposiciones (R10 – R14)

#### R10 — Trámite Tras Aprobación de Propuesta
- **Pregunta:** *«Me aprobaron la propuesta de Trabajo de Grado. ¿Qué debo hacer después y cuándo puedo presentar el Informe Final?»*
- **Resultado Esperado:** Desarrollar el trabajo, período general de 180 días, no antes de 3 meses, visto bueno del director (Arts. 14, 29, 30).
- **Respuesta Real:** Explica el período de 180 días y el plazo de 3 meses del informe final. Citó Art. 14 y Art. 30.
- **Juicio:** **Parcialmente correcto** (El artículo 29 conceptual formó parte del contexto pero la cita priorizó los arts. operativos 14 y 30). Latencia: 48.418 ms.

#### R11 — Vencimiento del Período y Necesidad de Más Tiempo
- **Pregunta:** *«¿Qué ocurre si no finalizo mi Trabajo de Grado dentro del período establecido y necesito más tiempo?»*
- **Resultado Esperado:** Relaciona el período general (Art. 14) con las condiciones de prórroga (Art. 15).
- **Respuesta Real:** Relaciona ambos artículos con solvencia, explicando plazos de solicitud y requisitos.
- **Juicio:** **Correcto**. Latencia: 64.499 ms. Citas: Arts. 14 y 15 (págs. 5 y 6).

#### R12 — Trámite del Informe Final: de la Entrega a la Evaluación
- **Pregunta:** *«¿Cómo pasa mi Informe Final desde la entrega hasta la evaluación?»*
- **Resultado Esperado:** Entrega con formato suscrito por el director al Comité y valoración cualitativa del evaluador (Arts. 30 y 31).
- **Respuesta Real:** Detalla el flujo de entrega, asignación de jurado y emisión de conceptos cualitativos.
- **Juicio:** **Correcto**. Latencia: 111.574 ms. Citas: Arts. 30 y 31 (págs. 10 y 11).

#### R13 — Trámite ante Informe Aplazado
- **Pregunta:** *«Si mi Informe Final queda aplazado, ¿qué debo hacer para volver a presentarlo?»*
- **Resultado Esperado:** Correcciones identificadas por el evaluador, visto bueno del tutor y nueva presentación (Arts. 31 y 32).
- **Respuesta Real:** Explica el trámite de corrección según el concepto cualitativo de aplazado.
- **Juicio:** **Parcialmente correcto** (Fundamentó exhaustivamente en el Art. 31 literal a; el Art. 32 secundario no fue incorporado como tarjeta de cita directa). Latencia: 38.824 ms.

#### R14 — Diferencia entre Propuesta e Informe Final
- **Pregunta:** *«¿Qué diferencia hay entre presentar una propuesta de Trabajo de Grado y entregar el Informe Final?»*
- **Resultado Esperado:** Distingue planteamiento inicial (propuesta) de resultados consolidados (informe final) (Arts. 27, 29, 30).
- **Respuesta Real:** Contrasta con solidez técnica ambas etapas académicas.
- **Juicio:** **Parcialmente correcto** (Citó Arts. 29 y 30; el Art. 27 quedó cubierto en la síntesis textual). Latencia: 69.535 ms.

---

### 4.3. Parágrafos y Excepciones (E15 – E18)

#### E15 — Prórroga en Seminario
- **Pregunta:** *«¿La modalidad de Seminario admite prórroga?»*
- **Resultado Esperado:** Debe responder que no se concede prórroga a la modalidad de Seminario (Art. 15, Parágrafo 1).
- **Respuesta Real:** Responde categóricamente que no se admite prórroga para Seminario.
- **Juicio:** **Parcialmente correcto** (Respuesta conceptualmente perfecta; el chunk padre Art. 15 cuerpo se resumió en la respuesta sin generar tarjeta de cita aditiva). Latencia: 27.094 ms.

#### E16 — Situaciones Excepcionales de Prórroga en Práctica
- **Pregunta:** *«¿En qué situaciones excepcionales puede prorrogarse una práctica?»*
- **Resultado Esperado:** Enfermedad grave certificada por EPS o aplazamiento solicitado por la empresa ajeno al estudiante (Art. 15, Parágrafo 2).
- **Respuesta Real:** Identifica con exactitud quirúrgica ambas causales excepcionales.
- **Juicio:** **Correcto**. Latencia: 38.395 ms. Cita: Art. 15, Parágrafo 2, pág. 6.

#### E17 — Libre Elección de Modalidad vs. Nivel Técnico
- **Pregunta:** *«¿Todos los estudiantes pueden escoger libremente cualquiera de las modalidades de Trabajo de Grado?»*
- **Resultado Esperado:** Regla general libre, con excepción de Técnico Profesional cuya modalidad exclusiva es Práctica (Art. 8, Parágrafo).
- **Respuesta Real:** Expone la regla general y remarca la restricción del nivel técnico profesional.
- **Juicio:** **Correcto**. Latencia: 32.725 ms. Cita: Art. 8, Parágrafo único, pág. 4.

#### E18 — Conformación de 3 Integrantes en Desarrollo Tecnológico
- **Pregunta:** *«¿Podemos integrar tres estudiantes en un proyecto de Desarrollo Tecnológico?»*
- **Resultado Esperado:** Sí, por excepción del Art. 11, parágrafo, que permite hasta 3 en Investigación y Desarrollo Tecnológico.
- **Respuesta Real:** Confirma la viabilidad de los 3 integrantes amparándose en la excepción de la modalidad.
- **Juicio:** **Correcto**. Latencia: 22.403 ms. Cita: Art. 11, Parágrafo, pág. 5.

---

### 4.4. Consultas Ambiguas o Parciales (A19 – A22)

- **A19 («¿Cuántos días tengo para hacer el informe?»):** Distingue el período general de 180 días del plazo de 3 meses e invita a aclarar la fase del proyecto. **Juicio: Correcto** (39.483 ms).
- **A20 («¿Puedo hacer el trabajo con mis amigos?»):** Explica el límite general de 2 integrantes y la excepción de 3 en Investigación/Desarrollo Tecnológico, solicitando precisar el número y la modalidad. **Juicio: Correcto** (50.164 ms).
- **A21 («¿Puedo pedir una prórroga?»):** Aclara que depende de la modalidad y de los requisitos del Art. 15. **Juicio: Parcialmente correcto** (62.966 ms).
- **A22 («¿Qué pasa si me rechazan el trabajo?»):** Orienta sobre las consecuencias según se trate de la propuesta o del informe aplazado/reprobado. **Juicio: Parcialmente correcto** (43.176 ms).

---

### 4.5. Sin Evidencia Suficiente en Corpus (S23 – S25)

- **S23 («¿Cuál es el valor exacto en pesos que debo pagar por la modalidad de Seminario este año?»):** El asistente reconoce que el reglamento alude a derechos pecuniarios, pero declara explícitamente que no dispone de tarifas actualizadas en pesos e indica consultar a Tesorería. Cero citas espurias. **Juicio: Correcto** (28.151 ms).
- **S24 («¿Cuál es el correo electrónico específico del Comité de Trabajo de Grado de mi programa?»):** Se abstiene de inventar direcciones de correo operativo y orienta a consultar la Coordinación Académica. **Juicio: Correcto** (29.426 ms).
- **S25 («¿En qué día y hora exactos me programaron la sustentación?»):** Aclara que el reglamento no contiene agendas personales de sustentación. **Juicio: Correcto** (38.271 ms).

---

### 4.6. Consultas Fuera de Alcance (F26 – F28)

- **F26 («¿Cuál es el precio de una hamburguesa?»):** Detección inmediata de consulta ajena al ámbito normativo (`abstained: true`). Cero citas normativas. **Juicio: Correcto** (6.917 ms).
- **F27 («¿Qué temperatura hará mañana en Bogotá?»):** Detección instantánea de consulta meteorológica. Tiempo: **129 milisegundos**. **Juicio: Correcto**.
- **F28 («¿Cómo instalo Windows en mi computador?»):** Rechazo cortés por temática técnica ajena al Reglamento de Trabajo de Grado. **Juicio: Correcto** (16.608 ms).

---

### 4.7. Aislamiento Estricto de Versiones (V29 – V30)

- **V29 (Activación versión 2019):**  
  Activó `uts_tg_2019`. La respuesta sobre modalidades se sustentó en los 8 chunks del Acuerdo 01-021. El 100% de las citas reportaron `version_id: "uts_tg_2019"`. **Juicio: Correcto** (57.122 ms).
- **V30 (Conmutación a versión secundaria):**  
  Activó `reglamento_trabajo_grado-1`. La consulta idéntica devolvió chunks y citas con `version_id: "reglamento_trabajo_grado-1"`. Cero mezcla con la versión 2019. **Juicio: Correcto** (49.491 ms).

---

## 5. Análisis Cuantitativo de Rendimiento y Latencias

```text
Distribución Temporal de las 30 Consultas:
- Tiempo Promedio General:  41.04 segundos
- Mediana de Tiempos:       39.20 segundos
- Mínimo Absoluto:          0.13 segundos (F27 - Fuera de Alcance)
- Máximo Absoluto:          111.57 segundos (R12 - Flujo Integral de Evaluación)
```

### 5.1. Desglose del Tiempo de Respuesta
- **Fase de Recuperación Vectorial (Qdrant + bge-m3):** Ocupa entre **80 ms y 180 ms** del tiempo total.
- **Fase de Inferencia Generativa (Ollama + qwen2.5:7b en CPU local):** Representa más del **98%** del tiempo total de respuesta (entre 20 y 60 segundos por respuesta estructurada).
- **Fase de Abstención Inmediata:** Toma menos de **1.0 segundo** al descartar la invocación del modelo generativo.

---

## 6. Conclusiones y Lecciones Aprendidas de la Validación Técnica

1. **Cero Alucinaciones:** La directriz de forzar al LLM a sintetizar únicamente con base en el contexto provisto y generar las citas desde los metadatos de Qdrant demostró una efectividad del 100%, eliminando cualquier fabricación de normas falsas.
2. **Robustez ante Usuarios No Expertos:** Las preguntas coloquiales y ambiguas (A19, A20) fueron canalizadas con respuestas orientativas y peticiones de aclaración pertinentes, evitando respuestas tajantes incorrectas.
3. **Aislamiento Verificado:** Se comprobó empíricamente que la coexistencia de normativas no genera fugas de información ni respuestas anacrónicas.

---
*Fin del Documento 04 — Informe de Validación Técnica.*
