# Inventario Documental — Etapa 2
## Corpus NORMATIVA-TG UTS

**Fecha de generación:** 2026-11-27  
**Responsable:** Sistema automatizado (Etapa 2 de desarrollo)

> [!IMPORTANT]
> Este inventario distingue formalmente entre los **documentos oficiales auténticos** (suministrados institucionalmente) y las **versiones documentales almacenadas** en la base de datos (que incluyen evidencias históricas de iteraciones previas). Todos los metadatos de vigencia y fechas de aprobación consignados provienen de evidencia documental directa demostrable en los encabezados y portadas.

---

## 1. Distinción entre Documentos Oficiales y Versiones en Base de Datos

- **Documentos oficiales auténticos suministrados:** 13 documentos (2 reglamentos, 2 procedimientos y 9 formatos institucionales derivados de Word). Suman exactamente **151 páginas** y **561 chunks** indexados.
- **Versiones documentales gestionadas en SQLite y Qdrant:** 14 versiones (las 13 anteriores más 1 copia histórica inconsistente heredada de la Iteración 1: `reglamento_trabajo_grado-1`, bloqueada con `is_active = 0` y `estado_revision = 'CON_DISCREPANCIAS'`). Las 14 versiones suman exactamente **170 páginas** y **742 chunks**.

---

## 2. Reglamentos Institucionales

| Código / ID Versión | Nombre Oficial | Acuerdo | Año | Fecha Aprobación | Páginas | SHA-256 (completo) | Ubicación Archivo | Estado Vigencia | Revisión Humana |
|---|---|---|---|---|---|---|---|---|---|
| **uts_tg_2021** (Acuerdo 01-026) | Reglamento de Trabajo de Grado 2021 | 01-026 | 2021 | 2021-07-27 | 27 | `49d96d5d991e6381698d34b5447f49c9cac9d3fb9eb10ac4b198aa8a2d3df142` | `documentos_fuente/reglamentos/reglamento_2021.pdf` | **VIGENTE** | PENDIENTE |
| **uts_tg_2019** (Acuerdo 01-021) | Reglamento de Trabajo de Grado 2019 | 01-021 | 2019 | 2019-07-18 | 19 | `7ed66bb0d80b147eadfc2590cfcade87b91d788a9ac316f21d0d33c15f3b48cb` | `documentos_fuente/reglamentos/reglamento_2019.pdf` | **HISTÓRICO** | APROBADO (Activo) |
| **reglamento_trabajo_grado-1** | Copia con Discrepancia de Identidad (Iteración 1) | 01-021 (declarado 2021 erróneamente) | 2019 | 2019-07-18 | 19 | `7ed66bb0d80b147eadfc2590cfcade87b91d788a9ac316f21d0d33c15f3b48cb` | `data/pdfs/reglamento_trabajo_grado-1_reglamento_trabajo_grado-1.pdf` | **INCONSISTENTE_BLOQUEADO** | CON_DISCREPANCIAS |

> [!NOTE]
> **Disponibilidad del Reglamento 2019:** El documento auténtico del Acuerdo 01-021 de 2019 (19 páginas, SHA-256 `7ed66bb0d8...`) se encuentra disponible y verificado en `documentos_fuente/reglamentos/reglamento_2019.pdf`.
> 
> **Aclaración sobre archivos sintéticos de prueba:** El archivo `data/pdfs/uts_tg_2019_reglamento_2019.pdf` (1.9 KB, 1 página) es un artefacto sintético generado temporalmente por los runners de prueba automatizados para validar casos de error de formato y no forma parte del corpus documental institucional ni del inventario oficial.

---

## 3. Procedimientos Institucionales (SIG)

| Código | Nombre | Versión | Fecha Aprobación | Páginas | SHA-256 | Archivo Fuente | Perfil |
|---|---|---|---|---|---|---|---|
| **P-DC-28** | Presentación de la Propuesta de Trabajo de Grado | V3.0 | 2024-04-25 | 10 | `0e56b9f9213e5eed97939b50d12ba0f29943c4fe59caa7c192c8fe08e6aed6d8` | `documentos_fuente/procedimientos/P-DC-28.pdf` | `procedimiento_institucional` |
| **P-DC-29** | Presentación del Informe Final de Trabajo de Grado | V3.0 | 2024-04-25 | 9 | `2cefaf4dd494484d3748bc9320395fefb6cee1f15ca52ee6d7af737fc0777a41` | `documentos_fuente/procedimientos/P-DC-29.pdf` | `procedimiento_institucional` |

---

## 4. Formatos Institucionales (9 Documentos Derivados de Word)

Todos los 9 formatos fueron convertidos de Word (DOC/DOCX) a PDF mediante LibreOffice headless en el pipeline oficial.

| Código | Versión | Formato Original | Páginas PDF | SHA-256 PDF Derivado | Estado Conversión | Carácter Normativo |
|---|---|---|---|---|---|---|
| **F-AM-04** | V18 | DOCX | 1 | `e4a4e55b1e17c4f1a40f09026a2ecf05b1ec64a76414abc481e702ab442ded01` | EXITOSO | Plantilla institucional vacía |
| **F-DC-124** | V2 | DOC | 12 | `e0bc9719826b1a5d1af53db1dc2309fb72bb5a04a917b96544d66301558dbf5b` | EXITOSO | Plantilla institucional vacía |
| **F-DC-125** | V2 | DOCX | 28 | `42e78e329d92648e28fd402fd548b764502cbbd5ca97899e2161463c46449d0a` | EXITOSO | Plantilla institucional vacía |
| **F-DC-126** | V2 | DOC | 3 | `456b9a2336ea8bd94062d61e6511121fe23f0f3f12cd19d5480ec87b5f4252db` | EXITOSO | Plantilla institucional vacía |
| **F-DC-127** | V2 | DOC | 11 | `2de3259d1b6ad1cf8fe5216324ea6e51ac240475f0f8997ee3b87e73621e0526` | EXITOSO | Plantilla institucional vacía |
| **F-DC-128** | V2 | DOCX | 24 | `f5030f920ec0839ede18f3020903f3d49d591766568f2e5c77a308b960028a6c` | EXITOSO | Plantilla institucional vacía |
| **F-DC-129** | V2 | DOCX | 3 | `2445ef49909a45bcde8a518a7f647aeaee81debaaa80d1ef3776ee0fdc6531c3` | EXITOSO | Plantilla institucional vacía |
| **F-DC-130** | V4 | DOCX | 1 | `0fbb5664fec90c9cf52ec924b8ddfe4aac336ec04cff2a392ae6fb96bcf624b0` | EXITOSO | Plantilla institucional vacía |
| **F-DC-196** | V2 | DOC | 3 | `4eb0387581e63885879881fbbc36f87cffdc915a0eb3770f551e8cd14415f8b9` | EXITOSO | Plantilla institucional vacía |

---

## 5. Respaldo Documental de Fechas de Aprobación y Vigencia

1. **Acuerdo 01-026 de 2021:**
   - **Evidencia documental:** Encabezado oficial: *"CONSEJO DIRECTIVO ACUERDO No. 01-026 (Bucaramanga, 27 de julio de 2021) Por el cual se adopta el Reglamento de Trabajo de Grado de las Unidades Tecnológicas de Santander"*.
   - **Vigencia:** VIGENTE. Deroga las disposiciones anteriores contrarias (Acuerdo 01-021).
2. **Acuerdo 01-021 de 2019:**
   - **Evidencia documental:** Encabezado oficial: *"CONSEJO DIRECTIVO ACUERDO No. 01-021 (Bucaramanga, Julio 18 de 2019) Por el cual se adopta el Reglamento de Trabajo de Grado de las Unidades Tecnológicas de Santander"*.
   - **Vigencia:** HISTÓRICO.
3. **Procedimientos P-DC-28 y P-DC-29:**
   - **Evidencia documental:** Metadatos de control del SIG: Versión 3.0, Fecha de aprobación: 25/04/2024.
   - **Vigencia:** VIGENTES en los procesos del SIG.
4. **Formatos Institucionales:**
   - **Evidencia documental:** Control de versiones del SIG (versiones institucionales V2, V4 y V18 en el rótulo del encabezado).
   - **Vigencia:** Plantillas operativas autorizadas para la gestión documental de trabajos de grado; no constituyen normas reglamentarias sustantivas.
