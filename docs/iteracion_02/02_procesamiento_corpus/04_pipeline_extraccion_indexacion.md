# Diagrama del Pipeline de Extracción e Indexación — Etapa 2
## NORMATIVA-TG UTS

---

## 1. Arquitectura General del Pipeline de Ingestión

```mermaid
flowchart TD
    subgraph Entrada ["1. Entrada Documental"]
        A1["PDFs Oficiales (Reglamentos, Procedimientos)"]
        A2["Formatos Word (DOC/DOCX)"]
        A3["Conversión LibreOffice Headless"] --> A4["PDFs Derivados con Capa de Texto"]
    end

    subgraph Perfiles ["2. Detección de Perfil"]
        B1{"Perfil de la Familia Documental"}
        B1 -->|RTG| P1["Perfil A: Reglamento Estructurado"]
        B1 -->|P-DC| P2["Perfil B: Procedimiento Institucional"]
        B1 -->|F-DC / F-AM| P3["Perfil C: Formato Institucional"]
        B1 -->|Otros| P4["Perfil D: Documento General"]
    end

    subgraph Extraccion ["3. Extracción Híbrida Página a Página"]
        E1["Carga de PDF (pdfplumber + pypdfium2)"]
        E2{"¿Página con >= 50 caracteres en texto?"}
        E1 --> E2
        E2 -->|Sí| E3["Extracción Directa (text_layer)"]
        E2 -->|No| E4["OCR Tesseract (spa, psm 6, 300 DPI)"]
        E3 --> E5["PageText (page_num, lines, method, conf)"]
        E4 --> E5
    end

    subgraph Segmentacion ["4. Segmentación Semántica"]
        S1["Procesador de Perfil"]
        S1 --> S2["Limpieza Repetitiva (clean_pages)"]
        S2 --> S3["Parser de Estructura"]
        S3 --> S4["NormativeChunk (contexto, artículos, páginas)"]
    end

    subgraph Calidad ["5. Controles de Calidad Previos a Activación"]
        Q1["QualityChecker"]
        Q1 --> Q2{"¿Errores Críticos?"}
        Q2 -->|Sí| Q3["Estado: PENDIENTE_REVISION (Bloquea activación)"]
        Q2 -->|No / Advertencias| Q4["Estado: PROCESADO / PENDIENTE_REVISION"]
    end

    subgraph Almacenamiento ["6. Indexación y Persistencia"]
        D1[("SQLite: normativa.db")]
        D2["Vectorizador Local: BGE-M3 (1024 dim)"]
        D3[("Qdrant: Colección 'normativa'")]
        Q4 --> D1
        Q4 --> D2
        D2 --> D3
        D1 -.->|Verificación de correspondencia 1:1| D3
    end

    A1 --> E1
    A4 --> E1
    E5 --> S1
    S4 --> Q1
```

---

## 2. Decisiones Técnicas Clave

1. **Decisión de extracción por página**: Cada página evalúa de forma autónoma si posee suficiente texto en la capa digital. El OCR solo se ejecuta en páginas escaneadas o vacías, garantizando velocidad y máxima fidelidad textual.
2. **Perfiles desacoplados**: La selección del procesador se define en la tabla `families.perfil_procesamiento`, permitiendo asociar cualquier documento a un perfil sin tocar el código fuente.
3. **Bloqueo preventivo de activación**: Documentos con discrepancias de acuerdo/año, artículos faltantes o desincronización entre SQLite y Qdrant quedan bloqueados para activación oficial.
