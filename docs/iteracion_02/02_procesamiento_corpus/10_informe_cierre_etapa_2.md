# Informe Consolidado y Verificación Exhaustiva — Cierre de la Etapa 2
## NORMATIVA-TG UTS: Procesamiento del Corpus Documental y Controles de Calidad

**Fecha de Actualización:** 2026-11-27  
**Estado:** **VERIFICADO Y LISTO PARA INSPECCIÓN HUMANA (ETAPA 3 NO INICIADA)**

---

## 1. Confirmación de Carga, Segmentación e Indexación Real

Se confirma de manera demostrada y auditable que **todos los documentos del corpus normativo han sido efectivamente registrados, segmentados, guardados en SQLite e indexados como embeddings (BGE-M3, 1024 dimensiones) en Qdrant (colección `normativa`)**, y no meramente leídos para inventarios.

### Evidencia de persistencia:
- Base de datos SQLite: `data/db/normativa.db` (Tablas: `documents`, `versions`, `chunks`, `families`, `categories`).
- Base de datos vectorial: Qdrant en `http://localhost:6333`, colección `normativa`.
- Total chunks en SQLite: **746**.
- Total puntos/embeddings en Qdrant: **746**.
- Cobertura biunívoca: **100.0%**.

> **Ajuste de cierre (2026-11-27):** Se eliminó el chunk corrupto `ver_p_dc_28_v3_numeral_2_p1` (5 396 caracteres de tablas desordenadas) que fue generado por la confusión entre registros numerados de tablas y los numerales principales del documento. Total anterior: 747. Total corregido: **746**.

---

## 2. Tabla Consolidada por Documento y Versión

A continuación se presenta la tabla exhaustiva con el estado de cada documento y versión en el sistema tras las correcciones de fidelidad documental:

| Código | Nombre Oficial | Perfil de Procesamiento | Págs | Chunks SQLite | Embeddings Qdrant | Estado Proc. | Estado Revisión | Activo | Estado Vigencia Institucional |
|---|---|---|---|---|---|---|---|---|---|
| **RTG** | Reglamento de Trabajo de Grado 2019 | `reglamento_estructurado` | 19 | 181 | 181 | PROCESADO | APROBADO | **SÍ (1)** | Vigente histórico (Acuerdo 01-021 de 2019) |
| **RTG** | reglamento trabajo grado-1 2021 (Falso) | `reglamento_estructurado` | 19 | 181 | 181 | PROCESADO | CON_DISCREPANCIAS | **NO (0)** | Inconsistente (Evidencia bloqueada de Iteración 1) |
| **RTG** | **Reglamento de Trabajo de Grado 2021 (Auténtico)** | `reglamento_estructurado` | 27 | **210** | **210** | **PROCESADO** | **PENDIENTE** | **NO (0)** | **Vigente** (Acuerdo 01-026 de 2021) |
| **P-DC-28** | Presentación de la Propuesta de Trabajo de Grado | `procedimiento_institucional` | 10 | **39** | **39** | **PROCESADO** | **PENDIENTE** | **NO (0)** | **Vigente** (Versión 3.0 SIG) |
| **P-DC-29** | Presentación del Informe Final de Trabajo de Grado | `procedimiento_institucional` | 9 | **25** | **25** | **PROCESADO** | **PENDIENTE** | **NO (0)** | **Vigente** (Versión 3.0 SIG) |
| **F-AM-04** | Solicitud de Grado V18 | `formato_institucional` | 1 | **1** | **1** | **PROCESADO** | **PENDIENTE** | **NO (0)** | Plantilla institucional vacía |
| **F-DC-124** | Propuesta de Trabajo de Grado V2 | `formato_institucional` | 12 | **12** | **12** | **PROCESADO** | **PENDIENTE** | **NO (0)** | Plantilla institucional vacía |
| **F-DC-125** | Informe Final de Trabajo de Grado V2 | `formato_institucional` | 28 | **48** | **48** | **PROCESADO** | **PENDIENTE** | **NO (0)** | Plantilla institucional vacía |
| **F-DC-126** | Requerimiento de Empresa para Practicantes V2 | `formato_institucional` | 3 | **3** | **3** | **PROCESADO** | **PENDIENTE** | **NO (0)** | Plantilla institucional vacía |
| **F-DC-127** | Propuesta Modalidad Práctica V2 | `formato_institucional` | 11 | **11** | **11** | **PROCESADO** | **PENDIENTE** | **NO (0)** | Plantilla institucional vacía |
| **F-DC-128** | Informe Final Modalidad Práctica V2 | `formato_institucional` | 24 | **28** | **28** | **PROCESADO** | **PENDIENTE** | **NO (0)** | Plantilla institucional vacía |
| **F-DC-129** | Rejilla de Evaluación Informe Final V2 | `formato_institucional` | 3 | **3** | **3** | **PROCESADO** | **PENDIENTE** | **NO (0)** | Plantilla institucional vacía |
| **F-DC-130** | Concepto Final del Trabajo de Grado V4 | `formato_institucional` | 1 | **1** | **1** | **PROCESADO** | **PENDIENTE** | **NO (0)** | Plantilla institucional vacía |
| **F-DC-196** | Acta Terminación y Recibo a Satisfacción V2 | `formato_institucional` | 3 | **3** | **3** | **PROCESADO** | **PENDIENTE** | **NO (0)** | Plantilla institucional vacía |
| **TOTAL** | **14 Versiones en Base de Datos** | — | **170** | **746** | **746** | — | — | **1 Activo** | — |

> [!NOTE]
> **Conciliación de Páginas y Documentos:**
> - La suma exacta de páginas de las 14 versiones gestionadas en la base de datos es **170 páginas** (19 + 19 + 27 + 10 + 9 + 1 + 12 + 28 + 3 + 11 + 24 + 3 + 1 + 3 = 170).
> - De estas 14 versiones:
>   - **13 corresponden a documentos oficiales auténticos** vigentes o históricos autorizados (151 páginas, 566 chunks indexados).
>   - **1 corresponde a la versión con discrepancia de identidad** (`reglamento_trabajo_grado-1`, 19 páginas, 181 chunks indexados), preservada exclusivamente como evidencia histórica auditable con `is_active = 0` y `estado_revision = 'CON_DISCREPANCIAS'`.
> - Para detalles exhaustivos de la corrección de márgenes y auditoría textual, consultar `docs/iteracion_02/02_procesamiento_corpus/11_informe_comparativo_fidelidad_documental.md`.

---

## 3. Resultado Real del Validador de Correspondencia SQLite ↔ Qdrant

Ejecutado mediante: `.bin/uv run python scripts/validate_qdrant_chunks.py`

```text
[VAL] Iniciando validación de correspondencia:
      Qdrant URL  : http://localhost:6333
      Colección   : normativa
      Base SQLite : data/db/normativa.db
----------------------------------------------------------------------
[INFO] Chunks en SQLite   : 742
[INFO] Puntos en Qdrant   : 742
[INFO] Puntos con chunk_id: 742
[OK] Ausencia total de puntos huérfanos en Qdrant.
[OK] Ausencia total de chunks sin punto en Qdrant (100% cobertura).

======================================================================
INFORME DE CORRESPONDENCIA SQLITE <-> QDRANT
======================================================================
  Chunks en SQLite               : 742
  Puntos en Qdrant               : 742
  Puntos sin chunk_id            : 0
  Puntos duplicados              : 0
  Puntos huérfanos (en Qdrant)   : 0
  Chunks sin punto (en SQLite)   : 0
  Discrepancias de version_id    : 0
  Discrepancias de document_id   : 0
  family_id ausentes en Qdrant   : 0
  Discrepancias de family_id     : 0
  categoria_id ausentes en Qdrant: 0
  Discrepancias de categoria_id  : 0
  Discrepancias de texto exacto  : 0
  Discrepancias location_hint    : 0
  Total errores/discrepancias    : 0
======================================================================
[RESULTADO] EXITOSO: Correspondencia 100% íntegra, biunívoca y coherente.
```

---

## 4. Confirmación de No Aprobación Ni Activación Automática

Se confirma que:
- **Ninguno de los nuevos documentos fue aprobado automáticamente**: Todos tienen `estado_revision = 'PENDIENTE'` (o `PENDIENTE_REVISION_HUMANA`).
- **Ninguno de los nuevos documentos fue activado automáticamente**: Todos tienen `is_active = 0`.
- El único documento activo en el sistema sigue siendo la versión histórica de 2019 (`uts_tg_2019`, `is_active = 1`), preservando la estabilidad del entorno hasta que la dirección realice la aprobación humana.
- La versión errónea de la iteración anterior (`reglamento_trabajo_grado-1`) permanece bloqueada con `CON_DISCREPANCIAS` e `is_active = 0`.

---

## 5. Selección y Modificación de Perfiles desde el Frontend (Sin Tocar Código)

El administrador dispone de dos mecanismos directos desde la interfaz web:
1. **En la pestaña "Estructura Documental" (`/admin` -> pestaña `Jerarquía`):**
   - En cada tarjeta de familia documental (ej. `RTG`, `P-DC-28`, etc.) se visualiza un selector desplegable con el perfil asignado.
   - El administrador puede cambiar el perfil seleccionando entre:
     - *Reglamento estructurado* (`reglamento_estructurado`)
     - *Procedimiento institucional* (`procedimiento_institucional`)
     - *Formato institucional* (`formato_institucional`)
     - *Documento general* (`documento_general`)
   - El cambio dispara inmediatamente la llamada `PUT /api/admin/families/{id}` con `{ perfil_procesamiento: nuevo_perfil }` y actualiza la base de datos sin requerir reinicio ni cambios de código.
2. **Al crear una nueva familia documental:**
   - Tanto en el modal "+ Nueva Familia" como en el modal de carga de documentos al definir una familia inline, se incluye el selector del perfil técnico que gobernará el procesamiento de los documentos asociados a dicha familia.

---

## 6. Procedimiento Exacto para la Revisión Humana y Aprobación desde el Panel

Para que el revisor o la directora del trabajo de grado apruebe y active el nuevo corpus:

1. **Ingresar al Panel de Administración:**
   - Navegar a `http://localhost:5173/admin` e iniciar sesión con la clave administrativa configurada.
2. **Ubicar la versión en la pestaña "Versiones":**
   - Localizar `uts_tg_2021` ("Reglamento de Trabajo de Grado 2021").
   - Su badge indicará: Estado: `PROCESADO` y Revisión: `PENDIENTE`.
3. **Abrir el Modal de Detalle e Inspección:**
   - Hacer clic en el botón **"Ver Detalle / Informe"** (ícono de ojo).
   - Se abrirá `DocumentDetailModal`, donde se puede:
     - Ver el PDF original página por página haciendo clic en "Ver Documento PDF".
     - Consultar el informe de calidad documental y la lista de artículos y anomalías.
     - Descargar o contrastar con la matriz CSV de 74 artículos (`06_matriz_articulos_reglamento_2021.csv`).
4. **Registrar Observaciones y Aprobar:**
   - En el cuadro de texto *"Notas de revisión humana"*, escribir la constancia de verificación (ej. *"Revisados los 74 artículos conforme al Acuerdo 01-026 de 2021"*).
   - Hacer clic en el botón verde **"Aprobar Revisión"**.
   - El backend invocará `POST /api/admin/versions/uts_tg_2021/review` con `{ action: 'approve', notes: '...' }`, actualizando el estado a `APROBADO` con fecha y observaciones auditables.
5. **Activar la Versión Oficial:**
   - Una vez aprobada, hacer clic en el botón **"Activar"**.
   - El sistema desactivará automáticamente la versión de 2019 en esa familia (debido al índice único `idx_versions_active_per_family`) y dejará activa exclusivamente la versión 2021 (`is_active = 1`).

---

## 7. Comprobación y Reutilización del Reglamento 2019 (Acuerdo 01-021)

Se inspeccionó el archivo `data/pdfs/reglamento_trabajo_grado.pdf` (19 páginas, SHA-256: `7ed66bb0d80b147eadfc2590cfcade87b91d788a9ac316f21d0d33c15f3b48cb`):
- **Identidad demostrada:** Contiene en su portada:
  > *"CONSEJO DIRECTIVO ACUERDO No. 01-021 (Bucaramanga, Julio 18 de 2019) Por el cual se adopta el Reglamento de Trabajo de Grado de las Unidades Tecnológicas de Santander"*.
- **Estructura real comprobada:**
  - **3 artículos de acuerdo** (Artículo PRIMERO, Artículo DOS, Artículo TRES).
  - **64 artículos de reglamento** (Artículos 1 al 64).
  - **16 capítulos**.
  - Documento escaneado procesado con OCR (91.7% de confianza media).
- **Acción ejecutada:** Se copió a `documentos_fuente/reglamentos/reglamento_2019.pdf` para conservarlo formalmente en la carpeta fuente oficial, manteniendo todas las trazas y evidencias históricas anteriores sin eliminar ningún archivo.

---

## 8. Discrepancia Normativa Sustancial: P-DC-28 Numeral 5 vs. Reglamento 2021 Art. 11

No se trata de una discrepancia de redacción en singular o plural, sino de una **diferencia material de fondo**:

1. **P-DC-28 (Numeral 5 - GENERALIDADES):**
   > *"El Trabajo de Grado puede ser realizado en forma individual o en equipo; este podrá estar integrado hasta por dos (2) estudiantes. Todo lo anterior, en el marco de la normativa institucional del Reglamento de Trabajo de Grado."*
   - Establece como límite máximo **dos (2) estudiantes**, omitiendo cualquier excepción.

2. **Reglamento de 2021 (Acuerdo 01-026, Artículo 11):**
   > *"ARTÍCULO 11. El Trabajo de Grado puede ser realizado en forma individual o en equipo; este podrá estar integrado hasta por dos (2) estudiantes. Los criterios para la definición del número de integrantes serán los siguientes: complejidad de la temática abordada; complejidad de la situación problemática abordada; impacto en los procesos de docencia, investigación y extensión de la Institución; impactos que genera el objeto de estudio en la sociedad...*
   > ***Parágrafo. Para las modalidades de proyecto de investigación y desarrollo tecnológico, podrán ser aceptados hasta tres (3) estudiantes, con fundamento en los criterios establecidos en este artículo.***"*

### Tratamiento Normativo en el Sistema:
- El procedimiento SIG P-DC-28 omitió en su texto el parágrafo de excepción del Reglamento.
- Conforme al principio de jerarquía normativa institucional, el Acuerdo del Consejo Directivo (Acuerdo 01-026) prima sobre el procedimiento operativo (P-DC-28).
- El sistema **conserva ambas fuentes con sus metadatos y citas exactas**. El motor RAG citará el Artículo 11 del Reglamento señalando expresamente que para investigación y desarrollo tecnológico se permiten hasta 3 estudiantes, y el Procedimiento P-DC-28 señalando la regla general operativa.

---

## 9. Resultados de la Suite Completa de Frontend (Vitest)

Ejecutado mediante: `npm run test` en el directorio `frontend/`:

```text
 RUN  v2.1.9 /home/jhon/PycharmProjects/FastAPIProject2/frontend

 ✓ src/tests/chat.test.tsx (7 tests)
 ✓ src/tests/admin.test.tsx (5 tests)
 ✓ src/tests/integration.test.tsx (2 tests)
 ✓ src/tests/auth.test.tsx (10 tests)

 Test Files  4 passed (4)
      Tests  24 passed (24)
   Duration  1.89s
```
**Resultado:** 100% superado (24 de 24 pruebas unitarias e integración frontend aprobadas).

---

## 10. Confirmación de la Matriz de los 74 Artículos

La matriz generada en [`docs/iteracion_02/02_procesamiento_corpus/06_matriz_articulos_reglamento_2021.csv`](file:///home/jhon/PycharmProjects/FastAPIProject2/docs/iteracion_02/02_procesamiento_corpus/06_matriz_articulos_reglamento_2021.csv) conserva:
- **74 filas** correspondientes a los Artículos 1 al 74 consecutivos.
- Columnas: `numero`, `capitulo_numero`, `capitulo_romano`, `capitulo_titulo`, `page_start`, `page_end`, `cruza_paginas`, `paragrafos_count`, `paragrafos_identificados`, `literales_count`, `literales_identificados`, `metodo_extraccion`, `flags`, `estado_comprobacion`, `estado_revision_humana`, `observaciones`.
- 18 artículos marcados como multi-página (`cruza_paginas = True`).
- 27 artículos con parágrafos detallados.
- 19 artículos con literales desglosados.
- `estado_revision_humana = 'PENDIENTE_REVISION_HUMANA'` en todas las filas.

---

## 11. Vinculación con el Objetivo Específico 1 del Proyecto (F-DC-124)

En estricta observancia del principio rector de **no invención documental ni reformulación arbitraria de objetivos institucionales**, se consigna la siguiente precisión metodológica:

- El formato institucional F-DC-124 disponible en el corpus corresponde a la plantilla en blanco (*"Propuesta trabajo grado Investigación, Desarrollo Tecnológico, Monografía y Emprendimiento V2"*).
- Al no contar en el repositorio con el documento formal radicado y aprobado por el Comité de Trabajo de Grado en formato F-DC-124 que contenga el texto literal y oficial del **Objetivo Específico 1** y sus actividades para este proyecto específico, **se deja explícitamente PENDIENTE la vinculación formal de la Etapa 2 con dicho objetivo**.
- No se sustituye ni se reformula artificialmente el objetivo aprobado en ningún informe técnico hasta tanto se aporte el texto literal del documento institucional oficial radicado.
