# Validación del Aislamiento entre Versiones Normativas
## Prueba de Gestión, Ingestión, Coexistencia y Conmutación de Reglamentos
**Proyecto:** NORMATIVA-TG UTS (F-DC-124 / F-DC-125)  
**Institución:** Unidades Tecnológicas de Santander (UTS)  
**Fecha de evaluación:** Noviembre de 2026  
**Estado:** Validación Técnica Exitosa  

---

## 1. Principio y Requisito No Negociable de Aislamiento

Uno de los principios de diseño más críticos y no negociables de **NORMATIVA-TG UTS** establece:

> **Regla de Aislamiento Normativo:**  
> *"Toda búsqueda en la base de datos vectorial y en SQLite filtra estrictamente por `version_id`; nunca se mezclan versiones de diferentes años o acuerdos. Una cita o fragmento recuperado debe pertenecer de forma inviolable a la versión que se encuentre activa en el sistema al momento de la consulta."*

Este requisito resuelve un problema común en los sistemas RAG tradicionales: la contaminación cruzada o alucinación cronológica, en la cual un modelo responde citando artículos de una normativa derogada o fusionando requisitos de reglamentos expedidos en distintas épocas.

---

## 2. Mecanismo Técnico de Aislamiento Implementado

El aislamiento se garantiza en tres barreras arquitectónicas concurrentes:

1. **Barrera en Base de Datos Relacional (SQLite):**
   - En la tabla `versions`, una restricción de negocio asegura que solo un registro posea el flag booleano `is_active = 1`. Al activar una versión mediante el endpoint `/api/admin/versions/{id}/activate`, se ejecuta una transacción atómica que establece `is_active = 0` para todas las demás versiones y `is_active = 1` para la seleccionada.
2. **Barrera en Base de Datos Vectorial (Qdrant):**
   - Cada punto indexado en la colección `normativa` almacena en su payload el campo `version_id` indexado como tipo `keyword`.
   - En el componente `src/normativa/retrieval/retriever.py`, toda consulta ejecutada mediante `query_points` aplica obligatoriamente la condición de filtrado:
     ```python
     query_filter = models.Filter(
         must=[
             models.FieldCondition(
                 key="version_id",
                 match=models.MatchValue(value=active_version.id)
             )
         ]
     )
     ```
   - Esto instruye al motor HNSW de Qdrant a restringir la búsqueda espacial única y exclusivamente al subconjunto de vectores identificados con dicho `version_id`.
3. **Barrera en Construcción de Citas (`citations.py`):**
   - Las citas no son redactadas por el modelo de lenguaje generativo, sino construidas de manera determinista a partir de los metadatos de los chunks devueltos por el recuperador. Si un vector no pertenece a la versión activa, es física y matemáticamente imposible que figure en la lista de citas retornada al usuario.

---

## 3. Entorno de Validación: Versiones Registradas

Para comprobar este aislamiento de manera reproducible en el entorno real, se emplean los dos registros normativos persistidos en la base de datos `data/db/normativa.db`:

| Parámetro | Versión Primaria (2019) | Versión Secundaria de Contraste (2021) |
| :--- | :--- | :--- |
| **Identificador (`version_id`)** | `uts_tg_2019` | `reglamento_trabajo_grado-1` |
| **Nombre Registrado** | Reglamento de Trabajo de Grado 2019 | reglamento trabajo grado-1 2021 |
| **Acto Administrativo** | Acuerdo No. 01-021 | Acuerdo No. 01-026 |
| **Año de Expedición** | 2019 | 2021 |
| **Fecha de Expedición** | 2019-07-18 | 2021-07-27 |
| **Estado de Vigencia** | Vigente histórico | Vigente |
| **Chunks en SQLite** | 181 chunks | 181 chunks |
| **Puntos Vectoriales en Qdrant** | 181 vectores (`size: 1024`) | 181 vectores (`size: 1024`) |
| **Total Vectores en Colección** | \multicolumn{2}{c|}{**362 vectores coexistiendo simultáneamente**} |

> [!NOTE]
> **Nota de Transparencia y Rigor Técnico:**  
> En el repositorio de desarrollo, el archivo binario cargado para la segunda versión de contraste (`reglamento_trabajo_grado-1`) corresponde al mismo documento PDF de 19 páginas utilizado para validar el pipeline de ingestión y la alternancia de versiones en bases de datos. Si la institución aprueba un nuevo Acuerdo oficial reformatorio con articulado diferente, dicho documento se carga directamente desde el panel administrativo `/admin`, completando la misma secuencia aquí comprobada.

---

## 4. Ejecución del Ciclo de Verificación de 10 Pasos

Se ejecutó la prueba formal de ciclo de vida de versiones a través de la API REST local:

### Paso 1: Carga de Normativa Inicial
- Se registró el documento `uts_tg_2019_reglamento_trabajo_grado.pdf` con el identificador `uts_tg_2019`.
- Se calculó el hash SHA-256: `7ed66bb0d80b147eadfc2590cfcade87b91d788a9ac316f21d0d33c15f3b48cb`.

### Paso 2: Procesamiento e Indexación
- El pipeline OCR extrajo las 19 páginas (91.71% de confianza media).
- Se limpiaron 206 líneas de encabezados/pies.
- Se generaron 181 chunks jerárquicos y se insertaron 181 vectores en Qdrant.

### Paso 3: Activación de la Versión 2019
- **Comando:** `POST /api/admin/versions/uts_tg_2019/activate` con header `X-Admin-Key`.
- **Respuesta API:**
  ```json
  {
    "success": true,
    "message": "Versión 'uts_tg_2019' activada exitosamente como versión global.",
    "version": { "id": "uts_tg_2019", "is_active": true }
  }
  ```

### Paso 4: Formulación de Consulta y Verificación de Citas (Prueba V29)
- **Consulta:** *«¿Cuáles son las modalidades de Trabajo de Grado?»*
- **Respuesta del Asistente:** Enumera las 6 modalidades según el artículo 8.
- **Auditoría de Citas y Chunks:**
  - `version_id` retornado en respuesta: `"uts_tg_2019"`.
  - Citas devueltas: 7 citas estructurales (Artículo 8, incisos a al f y parágrafo).
  - Verificación de pureza: El 100% de las citas poseen `version_id: "uts_tg_2019"`. Cero citas de `reglamento_trabajo_grado-1`.

### Paso 5: Carga de Segunda Normativa
- Se cargó un segundo documento con el identificador `reglamento_trabajo_grado-1` correspondiente al Acuerdo 01-026.
- Se indexaron exitosamente 181 chunks adicionales en la colección compartida `normativa`. Total de puntos en Qdrant: 362.

### Paso 6: Activación de la Segunda Versión
- **Comando:** `POST /api/admin/versions/reglamento_trabajo_grado-1/activate`
- **Respuesta API:**
  ```json
  {
    "success": true,
    "message": "Versión 'reglamento_trabajo_grado-1' activada exitosamente como versión global."
  }
  ```
- **Comprobación en `/api/versions/active`:**
  ```json
  {
    "active_version": {
      "id": "reglamento_trabajo_grado-1",
      "nombre": "reglamento trabajo grado-1 2021",
      "is_active": true
    }
  }
  ```

### Paso 7: Repetición de Consultas bajo la Nueva Versión (Prueba V30)
- **Consulta idéntica:** *«¿Cuáles son las modalidades de Trabajo de Grado?»*
- **Respuesta del Asistente:** Generada exitosamente.
- **Auditoría de Citas y Chunks:**
  - `version_id` retornado en respuesta: `"reglamento_trabajo_grado-1"`.
  - Citas devueltas: 7 citas estructurales.
  - Verificación de pureza: El 100% de las citas reportan `version_id: "reglamento_trabajo_grado-1"`.

### Paso 8: Comprobación de No Mezcla de Fuentes (Aislamiento Estricto)
- Se auditaron las trazas en SQLite (`SELECT * FROM traces WHERE id = ?`).
- En la consulta bajo `reglamento_trabajo_grado-1`, los 5 chunks devueltos por Qdrant presentaron exclusivamente el prefijo `reglamento_trabajo_grado-1_*`.
- **Tasa de contaminación documental:** **0.0%**. Ningún chunk de `uts_tg_2019` fue considerado como candidato de similitud ni inyectado en el contexto del LLM.

### Paso 9: Reactivación de la Versión Anterior (2019)
- **Comando:** `POST /api/admin/versions/uts_tg_2019/activate`
- **Respuesta API:** Activación inmediata en menos de 15 milisegundos.
- SQLite actualizó el registro atómicamente.

### Paso 10: Confirmación de Conservación de Datos e Índice
- Se verificó que la versión `uts_tg_2019` conservó íntegros sus 181 chunks en la tabla `chunks` de SQLite y sus 181 vectores en Qdrant.
- Una nueva consulta demostró que el asistente volvió a responder citando la versión `uts_tg_2019` sin necesidad de reindexar ni reprocesar el documento.

---

## 5. Tabla Resumen de Evidencias de Aislamiento

| Criterio de Evaluación | Resultado Esperado | Resultado Real Comprobado | Dictamen |
| :--- | :--- | :--- | :---: |
| **Conmutación en caliente** | Cambio de versión activa sin reiniciar backend ni Qdrant. | Ejecutado en < 20 ms vía endpoint REST. | **Superado** |
| **Aislamiento en Qdrant** | Búsqueda vectorial restringida al `version_id` activo. | 0 vectores de versiones inactivas recuperados. | **Superado** |
| **Aislamiento en Citas** | Citas generadas correspondientes 100% a la versión activa. | Coincidencia exacta de `version_id` en metadatos. | **Superado** |
| **Persistencia de Trazas** | Cada traza registra la versión exacta consultada. | Registrado en columna `version_id` de la tabla `traces`. | **Superado** |
| **Conservación de Índices** | Reversión de versión conserva índices previos intactos. | 362 puntos en Qdrant preservados sin pérdida de datos. | **Superado** |

---
*Fin del Documento 05 — Validación del Aislamiento entre Versiones.*
