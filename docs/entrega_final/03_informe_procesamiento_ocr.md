# Informe Definitivo de Procesamiento Documental y OCR
## Proyecto: Asistente Inteligente RAG para el Reglamento de Trabajo de Grado UTS
**Código Institucional:** F-DC-124 / F-DC-125  
**Institución:** Unidades Tecnológicas de Santander (UTS)  
**Fecha de consolidación:** Noviembre de 2026  
**Responsable Técnico:** Equipo Desarrollador NORMATIVA-TG UTS  

---

## 1. Identificación del Documento Fuente

| Parámetro | Detalle Institucional Comprobado |
| :--- | :--- |
| **Denominación Oficial** | Reglamento de Trabajo de Grado de las Unidades Tecnológicas de Santander |
| **Acto Administrativo** | Acuerdo del Consejo Directivo No. 01-021 |
| **Fecha de Expedición** | 18 de julio de 2019 (Bucaramanga, Santander) |
| **Número de Páginas** | 19 folios físicos digitalizados |
| **Archivo Local** | `data/pdfs/reglamento_trabajo_grado.pdf` |
| **Tamaño Binario** | 6.905.363 bytes (6.74 MB) |
| **Huella Digital SHA-256** | `7ed66bb0d80b147eadfc2590cfcade87b91d788a9ac316f21d0d33c15f3b48cb` |
| **Naturaleza del Archivo** | Documento rasterizado (escaneo óptico) sin capa de texto nativa incrustada |

---

## 2. Herramientas, Versiones y Configuración del Procedimiento OCR

El módulo de ingestión (`src/normativa/ingestion/extractor.py`) implementa un mecanismo de extracción híbrida condicional que evalúa la existencia de caracteres textuales antes de proceder a la rasterización óptica.

### 2.1. Pila Tecnológica de Ingestión
- **Motor de Renderizado:** `pypdfium2` (v4.30.0+), bindings en Python para Google PDFium (renderizado rasterizado a nivel de píxel en C++).
- **Motor de OCR:** `pytesseract` (v0.3.13+) sobre el binario de sistema `tesseract-ocr` (versión 5.x).
- **Extracción Digital Alternativa:** `pdfplumber` (v0.11.0+) para inspección de texto y tablas cuando existan PDFs nacidos digitales.
- **Normalización y Expresiones Regulares:** Módulo `re` estándar de Python 3.12 con soporte Unicode completo.

### 2.2. Parámetros de Configuración OCR Aplicados
- **Idioma del modelo lingüístico:** Español (`lang="spa"`).
- **Resolución espacial de renderizado:** 300 DPI (puntos por pulgada), escala óptima para maximizar la legibilidad de caracteres pequeños sin saturar la memoria RAM.
- **Espacio de color:** Escala de grises binarizada (`grayscale=True`).
- **Modo de segmentación de página (PSM):** Modo automático (PSM 3 o PSM 6 según orientación de línea).
- **Umbral de activación de OCR:** Si una página presenta menos de 50 caracteres en capa digital (`min_chars_digital = 50`), el extractor conmuta obligatoriamente a OCR.

---

## 3. Estadísticas de Confianza y Calidad por Página

### 3.1. Método Exacto de Cálculo de la Confianza OCR
La métrica de confianza OCR no es una invención probabilística del sistema ni debe confundirse con la exactitud semántica del texto. Se calcula extrayendo directamente el vector de confianza devuelto por el motor Tesseract para cada token de palabra identificado:

$$\text{Confianza Media de Página} = \frac{\sum_{i=1}^{N} \text{conf}_i}{N} \quad \forall \; \text{conf}_i \ge 0$$

Donde $N$ es el total de palabras reconocidas en la página que poseen un valor de confianza válido (descartando los delimitadores de bloque marcados con $-1$ por Tesseract).

### 3.2. Tabla Consolidada de Confianza Página por Página (Datos Reales)

| Página | Método Aplicado | Total Caracteres | Confianza OCR (%) | Estado de Calidad | Observaciones Técnicas |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **01** | OCR (300 DPI) | 2.136 | **92.4%** | Conforme | Preámbulo y considerandos iniciales. |
| **02** | OCR (300 DPI) | 1.900 | **75.5%** | **Baja Confianza** | Considerandos finales y firmas de acta previa. Ruido en tabla. |
| **03** | OCR (300 DPI) | 3.669 | **92.2%** | Conforme | Parte dispositiva del Acuerdo y Artículo 1 reparado. |
| **04** | OCR (300 DPI) | 2.976 | **92.4%** | Conforme | Modalidades de Trabajo de Grado (Artículos 8 a 10). |
| **05** | OCR (300 DPI) | 4.098 | **93.7%** | Conforme | Conformación de grupos (Art. 11), plazos (Art. 14). |
| **06** | OCR (300 DPI) | 3.945 | **93.1%** | Conforme | Régimen de prórrogas (Art. 15), pagos (Art. 16). |
| **07** | OCR (300 DPI) | 3.807 | **93.1%** | Conforme | Comités de Trabajo de Grado (Artículos 18 a 22). |
| **08** | OCR (300 DPI) | 3.458 | **92.4%** | Conforme | Funciones y directores de proyecto (Artículos 23 a 26). |
| **09** | OCR (300 DPI) | 3.472 | **92.5%** | Conforme | Presentación de propuesta (Artículos 27 a 28). |
| **10** | OCR (300 DPI) | 3.576 | **93.0%** | Conforme | Informe final y entrega al Comité (Artículos 29 a 30). |
| **11** | OCR (300 DPI) | 3.674 | **93.4%** | Conforme | Conceptos de evaluación: Aplazado, Aprobado (Art. 31-32). |
| **12** | OCR (300 DPI) | 3.443 | **92.5%** | Conforme | Menciones de honor y sustentación (Artículos 34 a 37). |
| **13** | OCR (300 DPI) | 3.918 | **92.7%** | Conforme | Modalidad Monografía y sus clases (Artículos 38 a 41). |
| **14** | OCR (300 DPI) | 3.515 | **92.9%** | Conforme | Modalidad Seminario e intensidad horaria (Art. 42-45). |
| **15** | OCR (300 DPI) | 3.899 | **93.1%** | Conforme | Modalidad Práctica (Artículos 46 a 48). |
| **16** | OCR (300 DPI) | 3.927 | **93.9%** | **Máxima Confianza** | Modalidades de práctica empresarial y comunitaria (Art. 49). |
| **17** | OCR (300 DPI) | 3.951 | **93.1%** | Conforme | Modalidad Emprendimiento y desarrollo empresarial. |
| **18** | OCR (300 DPI) | 3.315 | **92.8%** | Conforme | Régimen disciplinario, derechos de autor y propiedad intelectual. |
| **19** | OCR (300 DPI) | 1.427 | **87.8%** | Atención | Disposiciones finales, firmas del Presidente y Secretaria. |

### 3.3. Promedio Global del Documento
- **Páginas totales sometidas a OCR:** 19 de 19 páginas (100%).
- **Confianza Media Global:** **91.71%**.
- **Páginas con alerta de baja confianza (< 80%):** 1 sola página (Página 2, con 75.5%).

---

## 4. Diferenciación Crítica: Confianza OCR vs. Exactitud Textual Comprobada

Es un principio de rigor técnico diferenciar ambos conceptos:
1. **Confianza OCR (Estimación Heurística del Motor):** Es un valor estadístico generado internamente por la red neuronal de Tesseract basado en la nitidez del glifo, la distancia al prototipo de carácter y la ausencia de ambigüedad en el mapa de bits. Una confianza del 95% no garantiza que la palabra sea normativamente exacta (por ejemplo, puede confundir `Art. 1` con `Art. 4` con un 90% de confianza si el trazo está cerrado).
2. **Exactitud Textual Comprobada (Auditoría Humana frente al Original):** Es la verificación empírica manual, carácter por carácter y término por término, confrontando el texto digitalizado con el documento físico firmado.

---

## 5. Errores Detectados, Reparaciones Automáticas y Verificación frente al Original

Durante el proceso de ingestión y parseo estructural (`src/normativa/ingestion/parser.py`), el sistema identificó y subsanó automáticamente discrepancias causadas por la calidad del escaneo:

### 5.1. Reparación Estructural del Artículo 1 (Página 3)
- **Texto crudo extraído por el OCR:**  
  `ARTÍCULO 4. El presente documento es el marco general que se debe aplicar a los estudiantes delas...`
- **Diagnóstico del Parser:** El artículo se encuentra ubicado inmediatamente después del `CAPÍTULO I` y antecede cronológicamente al `ARTÍCULO 2`. El dígito `1` presentaba un artefacto de tinta superior que Tesseract interpretó como un `4`.
- **Acción Correctora Automatizada:** El parser aplicó una regla de reparación secuencial: al detectar que el artículo precedente esperado era el 1 y el texto posterior era el artículo 2, corrigió el ordinal a `ARTÍCULO 1` y generó una bandera de auditoría (`flag_numero_reparado: 1`).
- **Verificación contra el PDF Original:** Contrastado con la página 3 del documento físico oficial, el título reza exactamente: *«ARTÍCULO 1. El presente documento es el marco general...»*. La corrección fue **100% certera**.

### 5.2. Anomalías de Encabezados Detectadas en OCR
- **Anomalía en Página 2:** `Capítulo fuera de secuencia en página 2: CAPÍTULO V - DEL COMITÉ DE TRABAJO DE GRADO...`  
  *Causa:* En la página 2 del original se transcribió una cita en los considerandos que aludía al Capítulo V del reglamento anterior. El parser lo detectó como texto de considerando y evitó crear un capítulo espurio.
- **Anomalía en Página 3:** `Capítulo fuera de secuencia en página 3: CAPÍTULO | |`  
  *Causa:* Mancha de escaneo vertical que generó caracteres de barra. El parser lo descartó como ruido no secuencial.

### 5.3. Limpieza de Encabezados y Pies de Página Recurrentes (`cleaner.py`)
El módulo de limpieza analizó la recurrencia posicional vertical ($y_{top}, y_{bottom}$) en el 100% de las páginas. Aquellas líneas que se repitieron en más del 40% de las páginas fueron clasificadas y eliminadas:
- **Total de líneas de encabezado y pie eliminadas:** **206 líneas**.
- **Total de líneas de ruido óptico aisladas eliminadas:** **15 líneas**.
- **Líneas de índice y tablas de contenido eliminadas:** **13 líneas**.

Ejemplos reales de líneas institucionales depuradas:
- *«SACONSEJO DIRECTIVO - ACUERDO No. 01-021 (Bucaramanga, Julio 18 de 2019)»*
- *«Calle de los Estudiantes N. 9 - 82 Ciudadela Real de Minas»*
- *«Línea Gratuita Nacional: 018000 940203»*
- *«PBX: (+57) (7) 6917700»*
- *«Bucaramanga - Santander - Colombia»*

---

## 6. Verificación de Fechas, Plazos, Cantidades y Artículos Clave

Se ejecutó un cotejo manual exhaustivo entre el texto indexado y el PDF original para las disposiciones sustantivas:

| Elemento Normativo | Texto en PDF Original (Acuerdo 01-021) | Texto Extraído e Indexado en Sistema | Exactitud Comprobada |
| :--- | :--- | :--- | :---: |
| **Modalidades de Grado** | 6 modalidades: Inv., Des. Tec., Monografía, Seminario, Práctica, Emprendimiento. | Enumeradas taxativamente en Art. 8, incisos a) al f). | **100% Conforme** |
| **Período de Culminación** | 180 días calendario consecutivos tras aprobar propuesta. | "180 días calendario consecutivos a partir de..." (Art. 14, pág. 5). | **100% Conforme** |
| **Plazo Mínimo de Entrega** | No antes de transcurridos tres (3) meses. | "antes de transcurridos tres (3) meses a partir..." (Art. 30, par. 1, pág. 11). | **100% Conforme** |
| **Intensidad de Seminario** | Mínimo 160 horas académicas. | "mínimo de ciento sesenta (160) horas académicas" (Art. 42, par., pág. 14). | **100% Conforme** |
| **Conformación Grupal** | Máximo 2 estudiantes; excepción hasta 3 en Inv. y Desarrollo Tecnológico. | "máximo de dos (2)... hasta tres (3)..." (Art. 11 y par., pág. 5). | **100% Conforme** |
| **Conceptos de Evaluación** | Trabajo de Grado Aplazado, Aprobado y Reprobado. | Calificación cualitativa: Aplazado, Aprobado, Reprobado (Art. 31, pág. 11). | **100% Conforme** |
| **Clases de Monografía** | Monografía Teórica, de Análisis y de Sistematización de Experiencias. | Identificadas en el Capítulo IX, Art. 39 (pág. 13). | **100% Conforme** |
| **Modalidades de Práctica** | Práctica Empresarial y Práctica Social Comunitaria. | Clasificadas en el Capítulo XI, Art. 49 (pág. 16). | **100% Conforme** |

---

## 7. Estrategia de Segmentación y Chunks Reales Generados

### 7.1. Criterio de Chunking Jerárquico Normativo
En lugar de fragmentar ciegamente por cantidad arbitraria de caracteres o palabras con solapamiento (*sliding window*), lo que destruye el sentido jurídico de las leyes, el sistema adopta un **chunking jerárquico normativo**:
- Cada **Artículo** se preserva como unidad íntegra (cuerpo principal).
- Cada **Parágrafo** genera un chunk especializado aditivo vinculado a su artículo padre.
- Cada **Inciso** con contenido procedimental o sustantivo relevante genera un chunk atómico conservando el encabezado del artículo para no descontextualizar el literal.

### 7.2. Total Real de Chunks Producidos
Para el reglamento institucional de 2019 se generaron exactamente **181 chunks**:
- **Artículos de reglamento:** 64
- **Artículos de acuerdo resolutivo:** 3
- **Parágrafos específicos:** 36
- **Incisos y literales desglosados:** 78

### 7.3. Ejemplo Real de Chunks en Base de Datos

```json
{
  "id": "uts_tg_2019_art_14_cuerpo",
  "version_id": "uts_tg_2019",
  "capitulo_numero": 4,
  "capitulo_romano": "IV",
  "capitulo_titulo": "DEL PERÍODO PARA FINALIZAR EL TRABAJO DE GRADO",
  "articulo_numero": 14,
  "page_start": 5,
  "page_end": 5,
  "location_hint": "Capítulo IV - DEL PERÍODO PARA FINALIZAR EL TRABAJO DE GRADO, Artículo 14 (págs. 5-5)",
  "texto": "Capítulo IV - DEL PERÍODO PARA FINALIZAR EL TRABAJO DE GRADO. Artículo 14:\nEl período para finalizar el Trabajo de Grado aprobado en cualquiera de las modalidades de que trata este reglamento, será de ciento ochenta (180) días calendario consecutivos, a partir de la fecha de aprobación de la propuesta por parte del Comité de Trabajo de Grado del Programa.",
  "ocr_confidence": 93.7
}
```

---

## 8. Limitaciones del Procesamiento y Recomendaciones para Futuras Versiones

1. **Página 2 (Firma y Considerandos):** Presentó 75.5% de confianza OCR por presentar texto mecanografiado sobre sellos de radicación y firmas. Si bien esto afectó considerandos del acuerdo, no afectó el articulado sustantivo del reglamento.
2. **Recomendación Institucional:** Para futuras reformas o reglamentos expedidos por el Consejo Directivo de las UTS, se recomienda solicitar a la Secretaría General la entrega del documento en **formato PDF nativo digital** generado directamente desde el procesador de texto, lo que eliminará la necesidad de OCR y garantizará una fidelidad de caracteres del 100%.

---
*Fin del Documento 03 — Informe Definitivo de Procesamiento Documental y OCR.*
