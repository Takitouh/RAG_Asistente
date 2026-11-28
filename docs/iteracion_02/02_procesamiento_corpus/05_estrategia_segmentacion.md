# Estrategia de Segmentación — Etapa 2
## NORMATIVA-TG UTS

---

## Problema identificado en la iteración anterior

La segmentación anterior producía fragmentos truncados: algunos terminaban antes de incluir la información necesaria para responder una consulta. Los parágrafos podían quedar separados del artículo al que pertenecen, y los literales podían quedar sin el contexto del artículo padre.

---

## Estrategia seleccionada: Segmentación semántica por unidad estructural

### Principio fundamental
Cada chunk corresponde a **una unidad semántica completa** del documento original:

| Tipo de documento | Unidad mínima de chunk |
|-------------------|----------------------|
| Reglamento | Artículo completo (cuerpo) |
| Reglamento | Parágrafo + sus literales |
| Reglamento | Literal/inciso directo del artículo |
| Procedimiento | Sección numerada (o parte de ella) |
| Procedimiento | Actividad de tabla (fila completa) |
| Formato | Sección dentro de la página |
| General | Bloque de párrafos (≤2000 chars) |

### Preservación de contexto
Cada chunk incluye en su texto el **header de contexto** que indica:
- Capítulo (número romano + título)
- Artículo (número + tipo)
- Parágrafo (número o "único"), si aplica
- Literal (marcador), si aplica

Ejemplo de texto de chunk:
```
Capítulo IV - DE LOS PROCEDIMIENTOS GENERALES. Artículo 15, Parágrafo 2:
El estudiante deberá ...
```

### Continuidad entre páginas
Los artículos que cruzan páginas (18 de los 74 artículos del Reglamento 2021) mantienen una sola representación en la base de datos con `page_start` y `page_end` correctamente asignados. No se divide artificialmente un artículo por el límite de página.

### Relación entre fragmentos
El `chunk_id` preserva la relación jerárquica:
```
{version_id}_art_{numero}_cuerpo
{version_id}_art_{numero}_par_{paragrafo}
{version_id}_art_{numero}_inc_{literal}
```

### Separación texto original / texto normalizado
El texto del chunk es el texto limpio extraído (con reflow de líneas y limpieza de artefactos OCR). El texto original por página está disponible en los archivos JSON de `data/processed/`. La trazabilidad entre ambos se mantiene mediante `page_start` y `page_end`.

---

## Justificación de la estrategia

### Ventajas
1. **Sin truncamiento**: Ningún artículo, parágrafo o literal queda partido en su punto semántico.
2. **Localización precisa**: Las citas incluyen capítulo, artículo y página exacta.
3. **Aislamiento por versión**: `version_id` está en cada chunk; las búsquedas filtran por `version_id`.
4. **Artículos multi-página**: Se detectan y preservan correctamente.
5. **Verificable**: La matriz de artículos CSV permite revisar cada unidad manualmente.

### Limitaciones documentadas
1. **Artículos muy extensos**: No se subdividen (pueden superar el límite óptimo de tokens del LLM). En el Reglamento 2021 no se detectaron artículos que superen este límite.
2. **Formatos complejos**: Tablas con estructura muy visual pueden perder jerarquía.
3. **OCR**: La confianza del OCR es un indicador, no garantía de exactitud. Las páginas con OCR requieren revisión humana.
4. **Procedimientos en texto plano**: Si las actividades no están en tabla, el extractor de tablas no las captura.

---

## Resultados del Reglamento 2021

| Métrica | Resultado |
|---------|-----------|
| Artículos identificados | 74 |
| Artículos faltantes | 0 |
| Artículos que cruzan páginas | 18 |
| Artículos con parágrafos | 27 |
| Artículos con literales | 19 |
| Capítulos | 16 |
| Total parágrafos | 55 |
| Total literales/incisos | 89 |
| Reparaciones del parser | 0 |
| Anomalías detectadas | 0 |
| Método de extracción | text_layer (100%) |
