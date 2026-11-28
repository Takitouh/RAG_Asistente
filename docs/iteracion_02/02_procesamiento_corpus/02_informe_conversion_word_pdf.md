# Informe de Conversión de Formatos Word a PDF — Etapa 2
## NORMATIVA-TG UTS

**Fecha:** 2026-11-27  
**Herramienta:** LibreOffice en modo headless (`soffice --headless --convert-to pdf`)

---

## 1. Contexto y Objetivos

Para mantener la compatibilidad con el visor de PDF y el sistema de citas precisas por número de página del asistente NORMATIVA-TG UTS, los 9 formatos institucionales suministrados en formatos DOC y DOCX fueron convertidos a PDF preservando su capa de texto.

### Requisitos cumplidos:
1. **Conservación íntegra de los archivos originales**: Los 9 archivos DOC/DOCX se conservan intactos en `documentos_fuente/formatos/originales/`.
2. **Generación de PDFs derivados**: Almacenados en `documentos_fuente/formatos/pdf_derivados/`.
3. **Preservación estructural**: Se mantuvieron encabezados, tablas, instrucciones, rejillas y campos sin alteración intencional de contenido.
4. **Capa de texto nativa**: No se convirtieron los documentos a imágenes ni se forzó OCR sobre los documentos convertidos.
5. **Trazabilidad criptográfica**: Registro de huellas SHA-256 para archivos originales y PDFs derivados.
6. **Plantillas vacías autorizadas**: Únicamente se utilizaron plantillas institucionales vacías, sin incorporar datos personales ni formatos diligenciados.

---

## 2. Registro de Conversiones y Huellas SHA-256

| Código | Formato Original | Archivo Original | SHA-256 Original | Archivo PDF Derivado | SHA-256 PDF | Págs | Tablas | Estado |
|---|---|---|---|---|---|---|---|---|
| **F-AM-04** | DOCX | `F-AM-04 Solicitud Grado V18..docx` | `76cd525018ab...` | `F-AM-04 Solicitud Grado V18..pdf` | `e4a4e55b1e17...` | 1 | 4 | EXITOSO |
| **F-DC-124** | DOC | `F-DC-124 Propuesta trabajo grado... V2.doc` | `0e146bac0783...` | `F-DC-124 Propuesta trabajo grado... V2.pdf` | `e0bc9719826b...` | 12 | 14 | EXITOSO |
| **F-DC-125** | DOCX | `F-DC-125 Informe final trabajo grado... V2.docx` | `00d36eb0d0a1...` | `F-DC-125 Informe final trabajo grado... V2.pdf` | `42e78e329d92...` | 28 | 1 | EXITOSO |
| **F-DC-126** | DOC | `F-DC-126 Requerimiento de la empresa... V2.doc` | `fa91c73eb426...` | `F-DC-126 Requerimiento de la empresa... V2.pdf` | `456b9a2336ea...` | 3 | 5 | EXITOSO |
| **F-DC-127** | DOC | `F-DC-127 Propuesta de trabajo de grado_... V2.doc` | `6d8cae7b5302...` | `F-DC-127 Propuesta de trabajo de grado_... V2.pdf` | `2de3259d1b6a...` | 11 | 13 | EXITOSO |
| **F-DC-128** | DOCX | `F-DC-128 Informe final de trabajo de grado... V2.docx` | `193b6d9a87f4...` | `F-DC-128 Informe final de trabajo de grado... V2.pdf` | `f5030f920ec0...` | 24 | 2 | EXITOSO |
| **F-DC-129** | DOCX | `F-DC-129 Rejilla de evaluación informe final... V2.docx` | `0f8043e5251f...` | `F-DC-129 Rejilla de evaluación informe final... V2.pdf` | `2445ef49909a...` | 3 | 5 | EXITOSO |
| **F-DC-130** | DOCX | `F-DC-130 Concepto final del trabajo de grado V4..docx` | `a2b3ab317657...` | `F-DC-130 Concepto final del trabajo de grado V4..pdf` | `0fbb5664fec9...` | 1 | 3 | EXITOSO |
| **F-DC-196** | DOC | `F-DC-196 Acta de Terminación y Recibo... V2.doc` | `edd67a2485df...` | `F-DC-196 Acta de Terminación y Recibo... V2.pdf` | `4eb0387581e6...` | 3 | 3 | EXITOSO |

> [!TIP]
> El manifiesto auditable completo en formato JSON se encuentra en `documentos_fuente/formatos/manifest_conversion_word_pdf.json` y `docs/iteracion_02/02_procesamiento_corpus/02_informe_conversion_word_pdf.json`.

---

## 3. Verificación de Integridad de Contenido

- Se verificó que cada PDF derivado conserve las páginas y el texto editable (`text_layer`) mediante `pdfplumber`.
- No se produjeron omisiones de texto en tablas de rúbricas (ej. F-DC-129) ni en instrucciones de diligenciamiento (ej. F-DC-124).
- Las citas generadas por el motor RAG pueden referenciar la página exacta del PDF derivado de manera consistente con el visor frontend.
