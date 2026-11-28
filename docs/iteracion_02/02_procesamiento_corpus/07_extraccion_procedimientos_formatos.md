# Informe de Extracción y Verificación de Procedimientos y Formatos — Etapa 2
## NORMATIVA-TG UTS

---

## 1. Verificación de Procedimientos Institucionales

### 1.1 Procedimiento P-DC-28: Presentación de la Propuesta de Trabajo de Grado (Versión 3.0)
- **Archivo fuente:** `documentos_fuente/procedimientos/P-DC-28.pdf`
- **Páginas:** 10
- **Chunks indexados en SQLite y Qdrant:** **36**
- **Secciones generales identificadas (Numerales 1 al 9):**
  - Numeral 1: OBJETIVO (Pág. 1)
  - Numeral 2: ALCANCE (Pág. 1)
  - Numeral 3: DEFINICIONES Y/O ABREVIATURAS (Págs. 1-4)
  - Numeral 4: RESPONSABLE (Pág. 4)
  - Numeral 5: GENERALIDADES (Pág. 4)
  - Numeral 6: DOCUMENTOS DE REFERENCIA (Pág. 4)
  - Numeral 7: DESARROLLO Y/O DESCRIPCIÓN (Págs. 5-9)
  - Numeral 8: CONTROLES OPERACIONALES (Pág. 10)
  - Numeral 9: ANEXOS (Pág. 10)

- **Comprobación de elementos críticos solicitados (§9 del prompt):**
  - **Documentos de Referencia:** Extraídos en Numeral 6 (incluye F-DC-124, F-DC-126, F-DC-127, F-RI-07, F-RI-08, F-SIG-08, Reglamento de Trabajo de Grado).
  - **Numerales 7 y 7.1:** Subnumeral 7.1 extraído con su introducción y tabla completa de actividades.
  - **Requisitos de presentación de la propuesta:** Actividad 1 ("Elección de la modalidad de Trabajo de Grado").
  - **Soportes de pago:** Actividad 2 ("Pago del derecho pecuniario... hasta la octava (8ª) semana después del inicio de clases... comprobante de pago bancario").
  - **Responsabilidades de participantes:** Estudiante, Coordinador de Programa, Director de Trabajo de Grado, Comité de Trabajo de Grado, Evaluador.

### 1.2 Procedimiento P-DC-29: Presentación del Informe Final de Trabajo de Grado (Versión 3.0)
- **Archivo fuente:** `documentos_fuente/procedimientos/P-DC-29.pdf`
- **Páginas:** 9
- **Chunks indexados en SQLite y Qdrant:** **25**
- **Secciones generales identificadas (Numerales 1 al 9):**
  - Numeral 1: OBJETIVO (Pág. 1)
  - Numeral 2: ALCANCE (Pág. 1)
  - Numeral 3: DEFINICIONES Y/O ABREVIATURAS (Págs. 1-2)
  - Numeral 4: RESPONSABLE (Pág. 2)
  - Numeral 5: GENERALIDADES (Pág. 2)
  - Numeral 6: DOCUMENTOS DE REFERENCIA (Pág. 2)
  - Numeral 7: DESARROLLO Y/O DESCRIPCIÓN (Págs. 2-8)
  - Numeral 8: CONTROLES OPERACIONALES (Pág. 9)
  - Numeral 9: ANEXOS (Pág. 9)

- **Comprobación de elementos críticos solicitados (§9 del prompt):**
  - **Formatos del informe final:** Extraídos (F-DC-125, F-DC-128, F-DC-129, F-DC-130, F-DC-209).
  - **Plazos de evaluación y corrección:** Actividad 3 ("El evaluador dispone de cinco días hábiles para emitir el concepto... estudiante realiza correcciones en un tiempo máximo de 8 días hábiles").
  - **Procedimiento de programación de la sustentación:** Actividad 5 ("Fecha de sustentación del Informe Final... dentro de los 8 días hábiles siguientes").
  - **Responsabilidades:** Evaluador emite concepto, director avala con reporte de similitud antiplagio institucional, comité de trabajo de grado ratifica.

---

## 2. Verificación de Formatos Institucionales (9 Documentos)

Cada formato fue procesado bajo el perfil `formato_institucional`, generando fragmentos tipificados (`formato_seccion` y `formato_instruccion`), preservando tablas y distinguiendo plantilla de norma reglamentaria.

| Código | Formato | Págs | Chunks SQLite / Qdrant | Elementos Extraídos |
|---|---|---|---|---|
| **F-AM-04** | Solicitud de Grado | 1 | **1** | Datos del solicitante, requisitos de paz y salvo, opciones de grado |
| **F-DC-124** | Propuesta Trabajo de Grado | 12 | **12** | Título, planteamiento del problema, objetivos, justificación, cronograma, presupuesto |
| **F-DC-125** | Informe Final Trabajo de Grado | 28 | **48** | Estructura del informe, resumen, introducción, resultados, conclusiones, normas IEEE/APA |
| **F-DC-126** | Requerimiento de Empresa | 3 | **3** | Datos de la empresa, perfil del practicante, actividades propuestas, supervisor |
| **F-DC-127** | Propuesta Modalidad Práctica | 11 | **11** | Plan de trabajo de práctica, objetivos, cronograma, firmas de acuerdo |
| **F-DC-128** | Informe Final de Práctica | 24 | **28** | Informe de actividades de práctica, aportes a la empresa, conclusiones |
| **F-DC-129** | Rejilla de Evaluación Informe Final | 3 | **3** | Criterios de evaluación, escala cuantitativa/cualitativa, ponderaciones |
| **F-DC-130** | Concepto Final del Trabajo de Grado | 1 | **1** | Formato de concepto del director, aval de sustentación, firmas |
| **F-DC-196** | Acta de Terminación y Recibo a Satisfacción | 3 | **3** | Certificación de culminación de práctica a satisfacción de la empresa |
| **TOTAL** | **9 Formatos Institucionales** | **86** | **110** | **Total chunks indexados en SQLite y Qdrant** |

---

## 3. Detección de Contradicciones Normativas y Tratamiento en el RAG

Durante el análisis cruzado se identificaron discrepancias normativas entre documentos:
1. **Composición de grupos de trabajo de grado:**
   - *Reglamento 2021 (Art. 11):* Establece que el trabajo de grado se puede realizar en grupos de hasta 3 estudiantes según la modalidad, y contempla excepciones aprobadas por el Consejo Académico / Comité.
   - *Procedimiento P-DC-28 (Numeral 1 y 2):* En algunas modalidades operativas hace referencia general a "el estudiante" de manera singular.
   - **Tratamiento en el sistema:** Se conservaron ambas fuentes en su integridad y con su respectivo `location_hint`. El motor RAG no resuelve silenciosamente la contradicción ni elimina el texto del procedimiento; presenta la cita del Reglamento como norma jerárquica superior y la del procedimiento como instrucción operativa.

2. **Rango normativo de los formatos:**
   - Las instrucciones contenidas en F-DC-124 o F-DC-129 se tipificaron como `formato_instruccion`. Ningún formato tiene capacidad de derogar o modificar plazos establecidos en el Acuerdo 01-026 o en los Procedimientos SIG.
