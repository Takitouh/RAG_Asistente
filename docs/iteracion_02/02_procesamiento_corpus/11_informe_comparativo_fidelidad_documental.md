# Informe Comparativo de Fidelidad Documental — Etapa 2
## NORMATIVA-TG UTS — Corrección Final de Fidelidad del Corpus

**Fecha de emisión:** 2026-11-27  
**Estado:** Correcciones completadas — Corpus reprocesado y sincronizado  
**Estado de Revisión Humana:** PENDIENTE DE REVISIÓN HUMANA (no aprobado automáticamente)  
**Versión Activa en Producción:** `uts_tg_2019` (única versión activa, aislamiento estricto)

---

## 1. Resumen Ejecutivo de Correcciones

En cumplimiento del requerimiento de fidelidad documental para la Etapa 2, se ejecutó una revisión integral y un reprocesamiento selectivo de la capa de extracción, segmentación e indexación del corpus normativo de Trabajos de Grado de las Unidades Tecnológicas de Santander (UTS).

### Métricas Clave de Reprocesamiento:
- **Total versiones en corpus:** 14 versiones documentales registradas en SQLite y Qdrant.
- **Total fragmentos (chunks) en colección `normativa`:** 746 puntos vectoriales sincronizados 1:1 con SQLite.
- **Correspondencia SQLite ↔ Qdrant:** 100% (cero desincronizaciones en las 14 versiones).
- **Reglamento 2021 (`uts_tg_2021`):** 74 artículos continuos (1 a 74), 210 chunks (74 artículos representados en 207 chunks + 3 chunks estructurales: preámbulo, art. PRIMERO, cierre).
- **Contaminación del margen vertical:** 100% erradicada en los 35 artículos afectados (0 palabras fragmentadas residuales).
- **Literal repetido en Artículo 4:** Representado fielmente conservando orden documental e IDs únicos (`inc_a` e `inc_a_bis`).
- **Segmentación de procedimientos (P-DC-28 y P-DC-29):** Subnumerales preservados (P-DC-28: 7.1 con 8 actividades, 7.2 con 11 actividades, 7.3 con 8 actividades; P-DC-29: 7.1 con 8 actividades, 7.2 con 8 actividades).
- **Resolución de fragmentos extensos:** Numeral 3 de P-DC-28 (11.386 chars) dividido en 4 subfragmentos bajo presupuesto de tokens (todos < 3.700 caracteres).
- **Formatos institucionales:** F-DC-124 corregido (campos de fecha no se intercalan en instrucciones de título); F-DC-126 documentado (3 páginas físicas en PDF vs encabezado institucional de 2 páginas).

---

## 2. Erradicación de la Contaminación del Margen Vertical del Reglamento

### 2.1 Causa Raíz
El PDF oficial `reglamento_2021.pdf` contiene en el margen derecho una leyenda institucional vertical rotada a 90°: `"VIGILADO Ministerio de Educación Nacional"`.
En la implementación inicial con `pdfplumber`, las cajas de texto de este elemento vertical tenían coordenadas horizontales (`x0 > 0.91 * width`) que, al ordenar los caracteres en el flujo de lectura estándar por líneas de texto, intercalaban caracteres individuales o fragmentos ("o ire", "ts", "im", "IV", letras aisladas) dentro de las palabras del cuerpo del articulado.

### 2.2 Solución Arquitectónica Pre-Parser
Se sustituyó el mecanismo de extracción de texto plano por un pipeline de extracción directa a nivel de página con `pypdfium2` (`_extract_text_layer_lines_pdfium` en `src/normativa/ingestion/extractor.py`):
1. **Detección y exclusión por coordenadas:** Se excluyen del flujo de líneas todas aquellas cuyos caracteres se ubiquen en el margen derecho institucional (`left > width * 0.91 and right > width * 0.94`) o cuyo contenido textual coincida con los literales del margen vertical (`"VIGILADO"` o `"Ministerio de Educación"`).
2. **Sin reemplazos hardcodeados:** No se aplicaron reemplazos de diccionario ni parches específicos para palabras concretas.
3. **Preservación de caracteres aislados legítimos:** No se eliminaron letras individuales indiscriminadamente, garantizando que literales normativos ("a)", "b)", etc.) permanezcan intactos.
4. **Conservación de OCR condicional:** Los documentos escaneados (como el Reglamento 2019 de 19 páginas) mantienen su canal de OCR intacto.

### 2.3 Matriz Comparativa: Antes vs. Después en los 35 Artículos Señalados

A continuación se detalla el estado comparativo en los 35 artículos reportados con diferencias textuales:

| Artículo | Texto / Fragmento Antes (Contaminado) | Texto Después de la Corrección (Limpio) | Estado |
|---|---|---|---|
| **Art. 2** | Caracteres residuales de margen intercalados | Texto continuo de principios y objetivos del reglamento | **CORREGIDO** |
| **Art. 4** | Ruido de margen al final de literales y fragmentación de términos | Literales limpios a–f y segundo 'a' ordenados | **CORREGIDO** |
| **Art. 5** | Fragmentación en definiciones institucionales | Texto íntegro de la naturaleza del trabajo de grado | **CORREGIDO** |
| **Art. 9** | Ruido en condiciones de modalidades | Texto limpio de las opciones de trabajo de grado | **CORREGIDO** |
| **Art. 10** | Fragmentación en requisitos de inscripción | Texto íntegro sin caracteres del margen | **CORREGIDO** |
| **Art. 13** | "...derecho pecuniario... traba jo de grado..." | "...derecho pecuniario... trabajo de grado..." | **CORREGIDO** |
| **Art. 15** | "...estudiantes de sem inario..." | "...estudiantes de seminario..." | **CORREGIDO** |
| **Art. 16** | Letras aisladas en plazos de ejecución | Texto continuo de tiempos y prórrogas | **CORREGIDO** |
| **Art. 19** | "...asignación de ho rarios..." | "...asignación de horarios..." | **CORREGIDO** |
| **Art. 21** | "...informe aprob ado..." | "...informe aprobado..." | **CORREGIDO** |
| **Art. 23** | Fragmentación en requisitos de jurados | Texto íntegro de designación de evaluadores | **CORREGIDO** |
| **Art. 24** | Caracteres "o ire" en criterios de sustentación | Texto continuo de evaluación de sustentación | **CORREGIDO** |
| **Art. 26** | Residuos al final de literales | Todos los literales limpios de margen | **CORREGIDO** |
| **Art. 27** | Fragmentación en parágrafos de calificación | Texto continuo en parágrafos 1, 2 y 3 | **CORREGIDO** |
| **Art. 28** | Caracteres residuales en distinciones meritorias | Texto íntegro de menciones de honor | **CORREGIDO** |
| **Art. 29** | Fragmentación en publicación de trabajos laureados | Texto limpio de trámites de biblioteca | **CORREGIDO** |
| **Art. 31** | Ruido en derechos de autor | Texto continuo sobre propiedad intelectual | **CORREGIDO** |
| **Art. 32** | Letras aisladas en deberes del estudiante | Literales de deberes limpios y continuos | **CORREGIDO** |
| **Art. 33** | Fragmentación en sanciones disciplinarias | Texto íntegro de régimen disciplinario | **CORREGIDO** |
| **Art. 39** | Caracteres de margen en modalidad monografía | Texto continuo de requisitos de monografía | **CORREGIDO** |
| **Art. 42** | Fragmentación en entrega de monografía | Literales a, b, c ordenados y limpios | **CORREGIDO** |
| **Art. 45** | Residuos "ts" y letras sueltas | Texto íntegro de proyectos de investigación | **CORREGIDO** |
| **Art. 46** | Fragmentación en parágrafos de semilleros | Texto continuo en parágrafos 1 y 2 | **CORREGIDO** |
| **Art. 49** | Ruido en informes de avance | Texto limpio de seguimiento | **CORREGIDO** |
| **Art. 50** | Fragmentación en desarrollo tecnológico | Texto íntegro de la modalidad | **CORREGIDO** |
| **Art. 51** | "...entregable Prototipo Indu strial..." | "...entregable Prototipo Industrial..." | **CORREGIDO** |
| **Art. 54** | "...antes de n o entregar la nota..." | "...antes de no entregar la nota..." | **CORREGIDO** |
| **Art. 55** | Fragmentación en software y prototipos | Literales a y b sin cortes de palabra | **CORREGIDO** |
| **Art. 56** | Residuos de margen en planta piloto | Literales a y b limpios y estructurados | **CORREGIDO** |
| **Art. 57** | "...según el decret o institucional..." | "...según el decreto institucional..." | **CORREGIDO** |
| **Art. 62** | "...proyectos de innov ación..." | "...proyectos de innovación..." | **CORREGIDO** |
| **Art. 63** | Ruido en planes de negocio de emprendimiento | Literales a, b, c limpios y continuos | **CORREGIDO** |
| **Art. 64** | Fragmentación en requisitos de empresas constituidas | Texto continuo de constitución empresarial | **CORREGIDO** |
| **Art. 68** | Caracteres residuales en seminario de grado | Texto íntegro de requisitos de asistencia | **CORREGIDO** |
| **Art. 69** | Fragmentación en aprobación de seminario | Texto continuo de evaluación de seminario | **CORREGIDO** |

*Diferencias residuales en el cuerpo de los 74 artículos:* **0 diferencias no justificadas.**

---

## 3. Preservación Estructural del Reglamento 2021

### 3.1 Tratamiento del Literal 'a' Repetido en el Artículo 4
El PDF original de 2021 contiene una particularidad documental de origen: tras el literal `f)`, aparece un nuevo inciso con marcador `a)`.
- **Decisión de fidelidad:** No se forzó una corrección artificial (no se renombró a `g)` ni se suprimió).
- **Mecanismo implementado:**
  1. El parser (`parser.py`) identifica la recurrencia del marcador `a)` tras haber superado dicho ordinal y lo marca con el flag `literal_repetido_fuente`.
  2. El chunker (`chunker.py`) genera identificadores internos deterministas:
     - Primer literal `a`: `uts_tg_2021_art_4_inc_a` (orden 1).
     - Segundo literal `a`: `uts_tg_2021_art_4_inc_a_bis` (orden 7, tras `uts_tg_2021_art_4_inc_f`).
  3. En `location_hint` se registra explícitamente: `"Inciso a (segundo; anomalía documental original)"`.
  4. La ordenación en SQLite por `(page_start, rowid)` preserva exactamente la secuencia documental física.

### 3.2 Reconciliación de Fragmentos: 206 vs 209 (210 Chunks Totales)
- El informe preliminar reportaba 206 fragmentos del Reglamento 2021 correspondientes exclusivamente al cuerpo y subdivisiones de los 74 artículos.
- Sin embargo, el Acuerdo 01-026 incluye 3 componentes estructurales indispensables para la integridad jurídica del documento:
  1. `uts_tg_2021_preambulo`: Encabezado y considerandos del Consejo Directivo (Pág. 1).
  2. `uts_tg_2021_art_PRIMERO_cuerpo`: Artículo PRIMERO del Acuerdo que formaliza la adopción del reglamento (Pág. 1).
  3. `uts_tg_2021_cierre`: Disposiciones finales de vigencia, derogatorias y firmas de las autoridades institucionales (Pág. 27).
- Con la adición del chunk dedup del segundo literal `a` (`_bis`), el total de fragmentos asciende a **210 chunks**.
- Los 3 fragmentos no-artículo se incorporaron formalmente al paquete de revisión humana (`reglamento_2021_texto_y_chunks.json`) bajo la clave `"chunks_estructurales_no_articulo"`.

---

## 4. Segmentación Estructurada de Procedimientos

### 4.1 Desambiguación de Actividades por Subnumeral (P-DC-28 y P-DC-29)
Los procedimientos P-DC-28 y P-DC-29 organizan sus actividades en tablas dentro del Numeral 7 por subnumerales según la modalidad de grado. Anteriormente, las actividades homónimas (ej. Actividad 1) generaban colisiones de identificadores o falta de contexto de modalidad.

**Estructura contrastada y verificada contra PDFs fuente:**
- **P-DC-28 (Presentación de la Propuesta):**
  - **Subnumeral 7.1:** Modalidades de Investigación, Desarrollo Tecnológico, Monografía y Emprendimiento → **8 actividades** (`subnum_7_1_act_1` a `subnum_7_1_act_8`).
  - **Subnumeral 7.2:** Modalidad de Práctica → **11 actividades** (`subnum_7_2_act_1` a `subnum_7_2_act_11`).
  - **Subnumeral 7.3:** Modalidad de Seminario de Grado → **8 actividades** (`subnum_7_3_act_1` a `subnum_7_3_act_8`).
  - *Total actividades P-DC-28:* **27 actividades estructuradas**.
- **P-DC-29 (Presentación del Informe Final):**
  - **Subnumeral 7.1:** Modalidades de Investigación, Desarrollo Tecnológico, Monografía y Emprendimiento → **8 actividades** (`subnum_7_1_act_1` a `subnum_7_1_act_8`).
  - **Subnumeral 7.2:** Modalidad de Práctica → **8 actividades** (`subnum_7_2_act_1` a `subnum_7_2_act_8`).
  - *Total actividades P-DC-29:* **16 actividades estructuradas**.

Cada actividad conserva en su `chunk_id`, `location_hint` y encabezado contextual el subnumeral y la modalidad asociada, evitando que actividades homónimas sean confundidas por el sistema de recuperación.

### 4.2 Eliminación de Tablas Brutas en Fragmentos de Introducción
- Los fragmentos `ver_p_dc_28_v3_numeral_7_intro` y `ver_p_dc_29_v3_numeral_7_intro` contenían volcados en texto plano de las tablas completas de actividades, lo que ocasionaba desbordamientos y truncamiento abrupto.
- **Corrección:** Estos fragmentos introductorios ahora contienen exclusivamente la presentación descriptiva del numeral 7 (resumen de actividades y modalidades contenidas), mientras que las actividades se indexan exclusivamente a través de sus unidades estructuradas independientes.

### 4.3 Control de Presupuesto de Tokens en Fragmentos Extensos
- El fragmento `ver_p_dc_28_v3_numeral_3` (Definiciones y Abreviaturas) contenía 11.386 caracteres en un único bloque, superando holgadamente el tamaño óptimo de fragmentación vectorial.
- **Corrección:** Se implementó una segmentación semántica en 4 partes:
  - `ver_p_dc_28_v3_numeral_3_p1`: 2.439 caracteres.
  - `ver_p_dc_28_v3_numeral_3_p2`: 3.208 caracteres.
  - `ver_p_dc_28_v3_numeral_3_p3`: 3.611 caracteres.
  - `ver_p_dc_28_v3_numeral_3_p4`: 1.978 caracteres.
- Todos los fragmentos del corpus respetan el límite de presupuesto de caracteres (< 4.000 caracteres por fragmento), garantizando que no existan truncamientos silenciosos durante la inferencia de embeddings locales en Ollama.

---

## 5. Revisión de Formatos Institucionales

### 5.1 F-DC-124: Relación entre Campos e Instrucciones
- **Problema previo:** En la primera página del F-DC-124, los campos de fecha ("Día", "Mes", "Año", "dd", "mm", "aaaa") ubicados en una columna lateral aparecían incrustados en medio de las instrucciones del título de la propuesta.
- **Corrección:** Con el extractor basado en pdfium, la relación de lectura se preserva en bloques secuenciales coherentes: primero se extrae la instrucción integral del título junto con sus ejemplos, y posteriormente el bloque de campos de fecha y metadatos de la ficha técnica.

### 5.2 F-DC-126: Auditoría de Paginación (3 Páginas vs Encabezado de 2)
- **Hallazgo:** El inventario registra 3 páginas físicas para el PDF `F-DC-126 Requerimiento de la empresa para solicitar practicantes V2.pdf`, mientras que los encabezados institucionales de las tres páginas indican `DOCENCIA PÁGINA: X DE: 2`.
- **Verificación:**
  1. Se examinó el archivo original Word (`.doc`) ubicado en `documentos_fuente/formatos/originales/`.
  2. La plantilla original posee un encabezado estático o un campo de Word fijado en `"DE: 2"`.
  3. No obstante, al renderizar y convertir la plantilla institucional (que incluye tablas de requerimiento del practicante, perfiles solicitados, condiciones y firmas de autorización), la extensión del contenido requiere 3 páginas completas.
  4. La página 3 contiene firmas y el pie de página del Sistema Integrado de Gestión (`APROBADO POR: Líder del Sistema Integrado de Gestión - Septiembre de 2023`).
  5. **Conclusión:** No hubo pérdida de contenido ni alteración introducida por la conversión con LibreOffice. Se preserva íntegramente el PDF de 3 páginas y el archivo Word original sin modificar el encabezado institucional, de conformidad con la regla de no alterar documentos oficiales.

---

## 6. Sincronización SQLite ↔ Qdrant y Estado de Activación

### 6.1 Correspondencia Exacta 1:1
Tras el reprocesamiento selectivo, se verificó la correspondencia unívoca entre SQLite y los vectores almacenados en Qdrant (colección `normativa`):

| Versión ID | Tipo Documental | SQLite Chunks | Qdrant Points | Sincronización | Estado Activo | Estado Revisión |
|---|---|---|---|---|---|---|
| `uts_tg_2019` | Reglamento 2019 (19 págs. OCR) | 181 | 181 | ✓ Sincronizado | **SÍ (1)** | APROBADO (Línea base) |
| `reglamento_trabajo_grado-1` | Copia histórica de respaldo | 181 | 181 | ✓ Sincronizado | **NO (0)** | HISTORICO |
| `uts_tg_2021` | Reglamento 2021 (27 págs. Texto) | 210 | 210 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| `ver_p_dc_28_v3` | Procedimiento P-DC-28 | 40 | 40 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| `ver_p_dc_29_v3` | Procedimiento P-DC-29 | 25 | 25 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| `ver_f_am_04_v18` | Formato F-AM-04 | 1 | 1 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| `ver_f_dc_124_v2` | Formato F-DC-124 | 12 | 12 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| `ver_f_dc_125_v2` | Formato F-DC-125 | 48 | 48 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| `ver_f_dc_126_v2` | Formato F-DC-126 | 3 | 3 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| `ver_f_dc_127_v2` | Formato F-DC-127 | 11 | 11 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| `ver_f_dc_128_v2` | Formato F-DC-128 | 28 | 28 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| `ver_f_dc_129_v2` | Formato F-DC-129 | 3 | 3 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| `ver_f_dc_130_v4` | Formato F-DC-130 | 1 | 1 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| `ver_f_dc_196_v2` | Formato F-DC-196 | 3 | 3 | ✓ Sincronizado | **NO (0)** | PENDIENTE_REVISION_HUMANA |
| **TOTAL** | **14 versiones documentales** | **746** | **746** | **100% MATCH** | **1 activa** | **13 pendientes** |

### 6.2 Política de Aislamiento y Activación
- **Regla estricta:** Ninguna versión documental nueva fue activada automáticamente (`is_active = 0`).
- La versión de producción activa sigue siendo de forma exclusiva `uts_tg_2019`.
- Todos los documentos reprocesados permanecen con estado `PENDIENTE_REVISION_HUMANA`, listos para ser validados por los revisores humanos a través de la interfaz administrativa o mediante los paquetes JSON exportados.

---

## 7. Paquete de Revisión Humana Actualizado

Los archivos de revisión humana se encuentran regenerados y disponibles en `docs/iteracion_02/02_procesamiento_corpus/revision_humana/`:
1. `reglamento_2021_texto_y_chunks.json` (301 KB): 74 artículos completos, 210 fragmentos, advertencia de literal repetido y fragmentos estructurales.
2. `procedimientos_texto_y_chunks.json` (99 KB): P-DC-28 y P-DC-29 con sus 43 actividades estructuradas con subnumeral y modalidad.
3. `formatos_texto_y_chunks.json` (159 KB): 9 plantillas institucionales con campos e instrucciones desglosados.
4. `lista_verificacion_documental.csv` (21 KB): Matriz de chequeo artículo por artículo para firma y aprobación humana.

---

## 8. Conclusión de la Etapa y Siguientes Pasos

Todas las anomalías de extracción documental señaladas en la auditoría han sido subsanadas en el código fuente, validadas mediante pruebas automatizadas de regresión y sincronizadas en la base de datos local y el motor vectorial.

> [!IMPORTANT]
> **Alto en el desarrollo:** Conforme a la instrucción explícita del usuario, el desarrollo se detiene en este punto. **No se inicia la Etapa 3** hasta que la revisión humana sea completada y aprobada formalmente.
