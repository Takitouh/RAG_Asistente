# Informe Técnico: Estado Inicial del Prototipo y Discrepancias Documentales Identificadas

**Proyecto**: NORMATIVA-TG UTS — Asistente RAG para el Reglamento de Trabajo de Grado  
**Propuesta de Grado**: Código 65-2026-127 (F-DC-124)  
**Directora**: Laura Cristina Duarte Quintero  
**Iteración**: 02 — Etapa 1 de 5 (Gestión documental y versionamiento)  
**Fecha**: 27 de noviembre de 2026  

---

## 1. Resumen Ejecutivo

Durante la revisión del prototipo inicial por parte de la Dirección de Trabajo de Grado y las inspecciones de ingeniería de software sobre el repositorio, se identificó que, aunque el sistema era funcional para responder consultas básicas, presentaba limitaciones estructurales de diseño y una discrepancia crítica de identidad documental en el corpus precargado.

Este informe documenta la inspección forense del estado inicial (Commit `bcf7091017d1b51223f1c9c674ec2d196d4d9af2`), la verificación de las discrepancias C1 a C10 y las medidas adoptadas para corregir la inconsistencia de los acuerdos normativos.

---

## 2. Inspección Forense de la Base de Datos Inicial

Al inspeccionar la base de datos `data/db/normativa.db` previa a la migración, se extrajo la tabla de documentos y versiones:

```sql
SELECT id, filename, file_hash, file_size_bytes FROM documents;
```

**Resultado obtenido**:
- Registro 1: `doc_9fb89774cb`, Archivo: `uts_tg_2019.pdf`, Hash SHA-256: `7ed66bb0d80b147eadfc2590cfcade87b91d788a9ac316f21d0d33c15f3b48cb`
- Registro 2: `doc_1f53b95a1a`, Archivo: `reglamento trabajo grado-1.pdf`, Hash SHA-256: `7ed66bb0d80b147eadfc2590cfcade87b91d788a9ac316f21d0d33c15f3b48cb`

### Análisis Crítico:
1. **Colisión Absoluta de SHA-256**: Ambos registros referencian exactamente el mismo binario PDF byte a byte.
2. **Divergencia de Metadatos (Discrepancia C1 y C5)**:
   - El primer registro estaba asociado a la versión `uts_tg_2019` ("Reglamento de Trabajo de Grado 2019", Acuerdo 01-021).
   - El segundo registro estaba asociado a la versión `reglamento_trabajo_grado-1` etiquetado erróneamente con año `2021` y acuerdo `01-026`.
3. **Causa Raíz del Error**: Al subir el archivo `reglamento trabajo grado-1.pdf`, se creyó que correspondía a la reforma de 2021 (Acuerdo 01-026 de 74 artículos), cuando en realidad era una copia digital idéntica del Acuerdo 01-021 de 2019 (45 artículos).
4. **Consecuencia en el Asistente**: Cuando el usuario activaba "2021", el motor RAG citaba fragmentos del Acuerdo 01-021 de 2019 haciéndolos pasar por el Acuerdo 01-026 de 2021, violando el principio de fidelidad jurídica y académica.

---

## 3. Matriz de Discrepancias Técnicas (C1 a C10)

| Código | Discrepancia Observada en Prototipo 1 | Diagnóstico Técnico | Medida Correctiva Implementada en Etapa 1 |
| :--- | :--- | :--- | :--- |
| **C1** | Mezcla o confusión entre acuerdos 2019 y 2021 | Documento etiquetado como 2021 contenía el PDF de 2019 (SHA-256 idéntico). | Detección automática de duplicados SHA-256; versión falsa marcada con `inconsistencia_identidad=1` y bloqueada de activación. |
| **C2** | Modelo monopólico de versión única global | Solo podía haber 1 versión activa para todo el sistema, impidiendo documentos complementarios. | Desacoplamiento en Categorías, Familias y Versiones. Regla 6: activación por familia. |
| **C3** | Ausencia de documentos complementarios (P-DC-28, P-DC-29, F-DC-124, etc.) | La tabla de versiones sólo contemplaba el Reglamento de Trabajo de Grado. | Familias documentales independientes con código institucional (`codigo`). |
| **C4** | Inexistencia de categorización dinámica | Tipos de documentos hardcodeados o implícitos. | Entidad `categories` con CRUD administrable desde API y Frontend. |
| **C5** | Atribución errónea de citas normativas | El LLM intentaba deducir el acuerdo por texto alucinado. | Metadatos estrictos en chunks recuperados (`family_id`, `version_id`, `categoria_id`). |
| **C6** | Recuperación sin garantía de inmutabilidad del corpus | Si el admin cambiaba la versión activa durante una consulta, la recuperación se mezclaba. | Snapshot inmutable de versiones autorizadas (`authorized_version_ids`) al inicio de cada query. |
| **C7** | Trazas sin registro del corpus activo | La tabla `traces` sólo guardaba un campo simple `version_id`. | Incorporación de `authorized_versions_json` en SQLite para auditoría forense completa. |
| **C8** | Riesgo de activación de documentos incompletos | No existía validación obligatoria del estado del documento antes de activarlo. | Regla 10: Bloqueo de activación si `status != PROCESADO` o `estado_revision == RECHAZADO`. |
| **C9** | Confusión entre vigencia institucional y activación técnica | La activación se interpretaba equívocamente como vigencia legal. | Campo `estado_vigencia` (VIGENTE, DEROGADO, TRANSITORIO) desacoplado de `is_active`. |
| **C10** | Riesgo de eliminación en cascada destructiva | Borrado de registros sin validar dependencias normativas. | Regla 16: Restricción `RESTRICT` e impedimento explícito de borrado con dependencias. |

---

## 4. Estado de Preservación de Evidencias

Previo a cualquier modificación de código o esquema de base de datos:
1. **Commit de referencia Git**: `bcf7091017d1b51223f1c9c674ec2d196d4d9af2` registrado.
2. **Respaldo de Base de Datos**: Copia exacta preservada en:
   - Archivo: `data/backups/normativa_backup_iteracion_01.db`
   - Hash SHA-256: `a9b8058a0230231481e45eaaa39a08208342e21de5b828942791b419535c30df`
3. **Respaldo de Corpus y Trazas**: Se conservaron intactos los archivos PDF originales en `data/pdfs/` y las 140 trazas históricas registradas en la base de datos.
4. **Script de Reversión**: Se creó `scripts/restore_v1_backup.py` para permitir volver al estado inicial en caso de emergencia.
