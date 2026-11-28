# Perfiles de Procesamiento Documental — Etapa 2
## NORMATIVA-TG UTS

> [!NOTE]
> Los perfiles son configurables por familia documental desde la base de datos SQLite (campo `perfil_procesamiento` en la tabla `families`). No es necesario modificar código para asignar un perfil diferente a una familia nueva.

---

## Perfil A: Reglamento Estructurado (`reglamento_estructurado`)

**Implementado en:** `src/normativa/ingestion/profiles/reglamento.py`

### Unidades reconocidas
- **Preámbulo**: Texto antes del primer capítulo
- **Capítulos**: `CAPÍTULO I`, `CAPÍTULO II`, etc. (con reparación por secuencia)
- **Artículos**: `ARTÍCULO 1.`, `ARTÍCULO 2.`, etc. (con tolerancia a errores OCR)
- **Parágrafos**: `PARÁGRAFO`, `PARÁGRAFO 1.`, `PARÁGRAFO ÚNICO`
- **Literales/Incisos**: `a)`, `b)`, `1.`, `2.` dentro de artículos y parágrafos
- **Cierre**: Texto después de `PUBLÍQUESE`

### Continuidad entre páginas
Los artículos que continúan en páginas posteriores conservan las referencias `page_start` y `page_end`. El parser acumula líneas de continuación sin interrumpir el artículo hasta encontrar el siguiente marcador de artículo, capítulo o cierre.

### Estrategia de segmentación
Cada artículo genera:
1. Un chunk con el cuerpo principal del artículo
2. Un chunk por cada parágrafo (con sus literales incluidos)
3. Un chunk por cada literal/inciso directo del artículo (sin parágrafo)

**Ventaja:** Preserva unidades semánticas completas; ningún artículo queda partido.  
**Limitación:** Artículos muy largos no se subdividen; pueden superar el límite óptimo de tokens.

### Verificación configurable
El campo `expected_articles_count` en el perfil es configurable por versión. No está hardcodeado.

---

## Perfil B: Procedimiento Institucional (`procedimiento_institucional`)

**Implementado en:** `src/normativa/ingestion/profiles/procedimiento.py`

### Unidades reconocidas
- **Secciones numeradas**: `1. OBJETO`, `2. ALCANCE`, ..., `9. CONTROL DE CAMBIOS`
- **Subsecciones**: `7.1`, `7.2` dentro de la sección 7
- **Actividades (tabla)**: Número de actividad, nombre, descripción, responsable, registros

### Extracción de tablas
La extracción de actividades del numeral 7 se realiza directamente desde las tablas detectadas por `pdfplumber`. Cada fila de actividad genera un chunk independiente con todos sus campos (descripción, responsable, registros). Se evita mezclar columnas o filas diferentes.

### Estrategia de segmentación
- Secciones 1-6, 8-9: Un chunk por sección (o por parte si supera 1800 caracteres)
- Sección 7 (intro): Un chunk con texto introductorio
- Sección 7 (actividades): Un chunk por actividad de tabla

**Ventaja:** Preserva la relación actividad↔responsable↔registros.  
**Limitación:** Si las actividades están en texto plano (no tabla), el extractor de tablas no las captura.

---

## Perfil C: Formato Institucional (`formato_institucional`)

**Implementado en:** `src/normativa/ingestion/profiles/formato.py`

### Unidades reconocidas
- **Encabezado institucional**: Código (ej. F-DC-124), versión
- **Secciones numeradas** dentro del formato
- **Instrucciones**: Texto con palabras clave como "instrucción", "diligenciar", "criterio"
- **Campos de formulario**: Contenido de celdas de tabla

### Distinción plantilla vs. norma
Los chunks se marcan con `articulo_tipo = "formato_seccion"` o `"formato_instruccion"`. Los formatos no emiten rango normativo reglamentario.

### Estrategia de segmentación
Un chunk por sección dentro de cada página. Las secciones se detectan por encabezados numéricos.

**Ventaja:** Permite localizar instrucciones y campos específicos.  
**Limitación:** Formatos con estructura muy visual (tablas complejas) pueden perder su jerarquía.

---

## Perfil D: Documento General (`documento_general`)

**Implementado en:** `src/normativa/ingestion/profiles/general.py`

### Uso
Para documentos que no se ajustan a los perfiles A, B o C.

### Estrategia de segmentación
Segmentación por página y luego por bloques de párrafo (separados por doble salto de línea o por encabezados numéricos). Límite máximo de 2000 caracteres por chunk.

**Ventaja:** Universal; funciona para cualquier documento.  
**Limitación:** No reconoce estructuras semánticas propias del documento.

---

## Configuración por Familia

El administrador puede cambiar el perfil de cualquier familia desde el panel administrativo (campo `perfil_procesamiento` en la tabla `families`). Los perfiles disponibles son:

```
reglamento_estructurado
procedimiento_institucional
formato_institucional
documento_general
```

No es necesario modificar código para asignar un perfil a una familia nueva.
