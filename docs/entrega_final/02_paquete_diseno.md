# Paquete de Diseño del Prototipo NORMATIVA-TG UTS
## Documento de Arquitectura y Especificación de Diseño de Software
**Código Institucional:** F-DC-124 / F-DC-125  
**Institución:** Unidades Tecnológicas de Santander (UTS)  
**Fecha de consolidación:** Noviembre de 2026  
**Estado:** Arquitectura Realmente Implementada y Comprobada  

---

## 1. Visión General de la Arquitectura del Sistema

El sistema **NORMATIVA-TG UTS** adopta una arquitectura desacoplada, multicapa y estrictamente soberana (100% de ejecución local). El diseño garantiza que ningún dato, consulta institucional o fragmento documental sea transmitido a través de internet o procesado en plataformas de terceros.

```mermaid
flowchart TB
    subgraph Capa_Presentacion ["Capa de Presentación (Frontend Web)"]
        UI_Chat["Interfaz de Consulta Pública<br/>(React 18 + Vite + Tailwind CSS)"]
        UI_Admin["Panel Administrativo Seguro<br/>(Dashboard, Ingestión y Versiones)"]
        UI_PDF["Visor Confinado de PDF Original<br/>(Página exacta según cita)"]
    end

    subgraph Capa_API ["Capa de Exposición y Servicios (Backend FastAPI)"]
        API_Main["FastAPI Application (Port 8000)<br/>CORS Middleware + Cookie Auth"]
        R_Query["Query Router (/api/query)<br/>Validación Pydantic + Inferencia"]
        R_Versions["Versions Router (/api/versions)<br/>Consulta pública de versión activa"]
        R_Admin["Admin Router (/api/admin)<br/>Upload, Audit, OCR, Activation"]
    end

    subgraph Capa_Logica_RAG ["Capa Lógica de Negocio y RAG Soberano"]
        SVC_RAG["RAGService (Orquestador)<br/>Flujo de Consulta de Extremo a Extremo"]
        SVC_Intent["Intent & Social Detector<br/>Detección de cortesía y fuera de alcance"]
        SVC_Retriever["NormativeRetriever<br/>Filtro version_id + Expansión Jerárquica"]
        SVC_Generator["NormativeGenerator<br/>Prompt restringido + Disclaimer"]
        SVC_Citations["Citations Builder<br/>Citas deterministas desde metadatos"]
        SVC_Corpus["CorpusService<br/>Pipeline Ingestión + Chunker Jerárquico"]
    end

    subgraph Capa_Modelos_Locales ["Capa de Inteligencia Artificial Local (Ollama)"]
        OLLAMA_SRV["Servidor Ollama Local (Port 11434)"]
        M_EMBED["Modelo Embeddings: bge-m3<br/>(1024 dimensiones, multilingüe)"]
        M_LLM["Modelo Generativo: qwen2.5:7b<br/>(Inferencia densa instruida)"]
    end

    subgraph Capa_Persistencia ["Capa de Persistencia y Almacenamiento Local"]
        QDRANT["Qdrant Vector Database (Port 6333)<br/>Colección: 'normativa' (HNSW Cosine)"]
        SQLITE[("SQLite Database (data/db/normativa.db)<br/>documents, versions, chunks, traces")]
        FS_PDF["Almacenamiento Local de Archivos<br/>(data/pdfs/*.pdf)"]
    end

    UI_Chat -->|HTTP POST /api/query| R_Query
    UI_Chat -->|HTTP GET /api/versions/active| R_Versions
    UI_Admin -->|HTTP POST/GET con Cookie o Token| R_Admin
    UI_PDF -->|HTTP GET /api/admin/versions/.../pdf| R_Admin

    R_Query --> SVC_RAG
    R_Admin --> SVC_Corpus

    SVC_RAG --> SVC_Intent
    SVC_RAG --> SVC_Retriever
    SVC_RAG --> SVC_Generator
    SVC_RAG --> SVC_Citations
    SVC_RAG -->|Registra traza| SQLITE

    SVC_Retriever -->|Búsqueda con filtro version_id| QDRANT
    SVC_Retriever -->|Expansión jerárquica padre-hijo| SQLITE
    SVC_Retriever -->|Vectoriza consulta| M_EMBED

    SVC_Generator -->|Prompt con contexto normativo| M_LLM
    SVC_Corpus -->|Persiste metadatos y chunks| SQLITE
    SVC_Corpus -->|Guarda binario PDF confinado| FS_PDF
    SVC_Corpus -->|Vectoriza chunks e indexa| M_EMBED
    SVC_Corpus -->|Inserta puntos vectoriales| QDRANT

    M_EMBED --- OLLAMA_SRV
    M_LLM --- OLLAMA_SRV
```

---

## 2. Diagrama de Componentes del Sistema

El backend se organiza en seis módulos cohesivos bajo `src/normativa/`:

```mermaid
classDiagram
    class IngestionModule {
        +extract_pages(pdf_path, force_ocr)
        +clean_pages(pages, options)
        +parse_document(clean_pages)
    }

    class CorpusModule {
        +register_document(...)
        +process_and_index_version(...)
        +build_chunks_from_parsed_document(...)
        +get_version(id)
        +get_active_version()
        +set_active_version(id)
    }

    class RetrievalModule {
        +retrieve(query, version_id, top_k)
        +expand_hierarchy(chunks, version_id)
        +index_chunks(chunks, version_id)
    }

    class GenerationModule {
        +generate_answer(query, context)
        +build_citations(chunks)
        +is_greeting_or_social(query)
    }

    class TracingModule {
        +insert_trace(trace)
        +get_traces_summary()
    }

    class ApiModule {
        +query_router
        +admin_router
        +public_versions_router
    }

    ApiModule --> CorpusModule
    ApiModule --> RetrievalModule
    ApiModule --> GenerationModule
    ApiModule --> TracingModule
    CorpusModule --> IngestionModule
    CorpusModule --> RetrievalModule
    RetrievalModule --> CorpusModule
    GenerationModule --> RetrievalModule
```

---

## 3. Modelo de Datos Relacional (SQLite)

La base de datos relacional opera sobre el motor nativo `sqlite3` de Python en `data/db/normativa.db`. Alberga cuatro tablas diseñadas para mantener la integridad referencial y auditoría:

```mermaid
erDiagram
    DOCUMENTS ||--o{ VERSIONS : "ampara"
    VERSIONS ||--o{ CHUNKS : "contiene"
    VERSIONS ||--o{ TRACES : "atiende"

    DOCUMENTS {
        string id PK "doc_xxxx (UUID corto)"
        string filename "Nombre original del PDF"
        string file_path "Ruta confinada en data/pdfs/"
        string file_hash "SHA-256 del contenido binario"
        integer file_size_bytes "Tamaño en bytes"
        string uploaded_at "Marca de tiempo ISO-8601"
    }

    VERSIONS {
        string id PK "Identificador único (ej: uts_tg_2019)"
        string document_id FK "Referencia a documents.id"
        string nombre "Nombre representativo del reglamento"
        string numero_acuerdo "Acuerdo que expide la norma"
        integer anio "Año de expedición"
        string fecha_expedicion "Fecha formal (YYYY-MM-DD)"
        string estado_vigencia "Vigente / Derogado / Histórico"
        string status "RECIBIDO / PROCESADO / APROBADO"
        string status_message "Detalle del estado del proceso"
        boolean is_active "1 si es la versión global activa, 0 si no"
        string created_at "Fecha de registro"
        string updated_at "Fecha de última modificación"
        string activated_at "Fecha en que se activó"
        string report_json "Resumen estadístico del parseo y OCR"
        integer chunks_count "Total de chunks indexados"
    }

    CHUNKS {
        string id PK "version_id_art_X_inc_Y"
        string version_id FK "Referencia a versions.id"
        string document_id FK "Referencia a documents.id"
        string document_name "Nombre del archivo fuente"
        integer capitulo_numero "Número arábigo del capítulo"
        string capitulo_romano "Número romano (ej: III)"
        string capitulo_titulo "Título temático del capítulo"
        integer articulo_numero "Número arábigo del artículo"
        string articulo_ordinal "Ordinal o identificador especial"
        string articulo_tipo "reglamento / acuerdo"
        string paragrafo_numero "Identificador de parágrafo"
        string inciso_marker "Literal o viñeta (a, b, c...)"
        integer page_start "Página física inicial en el PDF"
        integer page_end "Página física final en el PDF"
        string texto "Contenido textual íntegro"
        float ocr_confidence "Confianza media estimada (0-100)"
        string location_hint "Encabezado contextual de cita"
        string created_at "Fecha de creación"
    }

    TRACES {
        string id PK "UUID v4 de la consulta"
        string created_at "Fecha y hora UTC"
        string version_id FK "Versión activa consultada"
        string query "Texto exacto de la pregunta"
        string response "Texto exacto generado"
        boolean abstained "1 si hubo abstención, 0 si no"
        string retrieved_chunks_json "JSON con chunks recuperados y scores"
        float latency_ms "Latencia total en ms"
        string citations_json "JSON con citas estructuradas"
        string abstention_reason "Causa técnica de abstención"
        float retrieval_ms "Tiempo de recuperación vectorial en ms"
        float generation_ms "Tiempo de inferencia del LLM en ms"
        float total_ms "Tiempo total percibido en ms"
        string execution_status "normal / social / abstention / error"
        string error_message "Mensaje de excepción si falló"
        string query_type "normative / greeting / out_of_scope"
        string context_chunks_json "JSON con chunks enviados al LLM"
    }
```

---

## 4. Estructura de Colecciones y Payloads en Qdrant

La persistencia vectorial reside en **Qdrant**, ejecutado dentro de un contenedor Docker local sobre el puerto `6333`.

### 4.1. Configuración de la Colección `normativa`
- **Dimensión vectorial:** `1024` (coincidente con la arquitectura de embeddings densos de `bge-m3`).
- **Función de distancia:** `Cosine` (Similitud del Coseno, espacio normalizado $[-1, 1]$).
- **Almacenamiento de Payload en disco:** `on_disk_payload: true` para optimizar el consumo de memoria RAM en hardware modesto.
- **Índice HNSW:** `m = 16`, `ef_construct = 100`, con full scan threshold en 10.000 puntos.

### 4.2. Esquema de Payload Almacenado por Punto Vectorial
Cada vector indexado en Qdrant almacena el siguiente payload estructurado:
```json
{
  "chunk_id": "uts_tg_2019_art_8_inc_a",
  "version_id": "uts_tg_2019",
  "document_id": "doc_9fb89774cb",
  "document_name": "reglamento_trabajo_grado.pdf",
  "capitulo_numero": 3,
  "capitulo_romano": "III",
  "capitulo_titulo": "DE LAS MODALIDADES DE TRABAJO DE GRADO",
  "articulo_numero": 8,
  "articulo_ordinal": null,
  "paragrafo_numero": null,
  "inciso_marker": "a",
  "page_start": 4,
  "page_end": 4,
  "location_hint": "Capítulo III - DE LAS MODALIDADES DE TRABAJO DE GRADO, Artículo 8, Inciso a (págs. 4-4)",
  "texto": "Capítulo III - DE LAS MODALIDADES DE TRABAJO DE GRADO. Artículo 8, Inciso a):\nProyecto de Investigación",
  "ocr_confidence": 92.4
}
```
**Índice de Payload en Qdrant:**  
Se crea un índice de tipo `keyword` sobre el campo `version_id`. Esto permite que las consultas realicen un filtrado exacto y en tiempo constante previo a la búsqueda HNSW, evitando el recorrido de vectores pertenecientes a normativas inactivas.

---

## 5. Flujos Principales de Procesamiento y Operación

### 5.1. Flujo de Ingestión Documental, Extracción y OCR
El pipeline de ingestión procesa el documento en cuatro fases sucesivas e inmutables:

```mermaid
flowchart TD
    A["PDF Oficial del Reglamento"] --> B["Extractor Híbrido<br/>(extractor.py)"]
    B --> C{"¿Tiene capa de texto<br/>>= 50 caracteres y sin force_ocr?"}
    C -->|Sí| D["Extracción digital directa con pdfplumber"]
    C -->|No| E["Renderizado a 300 DPI con pypdfium2<br/>+ OCR en español con Tesseract (spa)"]
    D --> F["PageText con líneas y coordenadas"]
    E --> F
    F --> G["Módulo de Limpieza (cleaner.py)<br/>Detecta frecuencia de encabezados y pies (>40%)"]
    G --> H["CleanPage (Texto depurado sin ruido de página)"]
    H --> I["Parser Normativo Estructural (parser.py)<br/>Reconoce Capítulos, Artículos, Parágrafos e Incisos"]
    I --> J["ParsedDocument + Reparación de Anomalías"]
```

### 5.2. Flujo de Segmentación Jerárquica y Vectorización

```mermaid
flowchart TD
    A["ParsedDocument"] --> B["Chunker Normativo Jerárquico<br/>(corpus/chunker.py)"]
    B --> C["Cuerpo de Artículos completos"]
    B --> D["Parágrafos aditivos vinculados"]
    B --> E["Incisos y literales desglosados"]
    C --> F["Chunks Estructurados con location_hint y metadatos"]
    D --> F
    E --> F
    F --> G["Persistencia relacional en SQLite (tabla chunks)"]
    F --> H["Generación de Embeddings locales<br/>(Ollama POST /api/embeddings modelo bge-m3)"]
    H --> I["Upsert en Batch a Colección Qdrant 'normativa'<br/>con payload version_id"]
```

---

### 5.3. Flujo de Consulta RAG y Generación Fundamentada (Diagrama de Secuencia)

El siguiente diagrama detalla la secuencia exacta que ocurre durante una consulta formulada por un estudiante:

```mermaid
sequenceDiagram
    autonumber
    actor Estudiante as Estudiante / Usuario
    participant UI as Frontend React (ChatPage)
    participant API as FastAPI (/api/query)
    participant RAG as RAGService
    participant Intent as Intent & Social Detector
    participant Retr as NormativeRetriever
    participant Qdr as Qdrant Vector DB
    participant Exp as Hierarchical Expander
    participant Gen as NormativeGenerator
    participant Oll as Ollama (qwen2.5:7b)
    participant DB as SQLite (normativa.db)

    Estudiante->>UI: Ingresa pregunta: "¿Cuáles son las modalidades...?"
    UI->>API: POST /api/query {"query": "..."}
    API->>RAG: query(query_text)
    
    RAG->>Intent: is_greeting_or_social(query)
    alt Es saludo o cortesía social
        Intent-->>RAG: (True, "Hola, soy el asistente...", "greeting")
        RAG->>DB: Registra traza rápida
        RAG-->>API: RAGResponse con respuesta social directa
        API-->>UI: QueryResponse
    else Es consulta sustantiva
        Intent-->>RAG: (False, None, None)
        RAG->>DB: Consulta versión activa global (get_active_version)
        DB-->>RAG: NormativeVersion (uts_tg_2019)
        
        RAG->>Retr: retrieve(query, version_id="uts_tg_2019", top_k=5)
        Retr->>Oll: POST /api/embeddings (bge-m3)
        Oll-->>Retr: Vector denso de 1024 floats
        
        Retr->>Qdr: query_points(vector, filter={version_id: "uts_tg_2019"})
        Qdr-->>Retr: ScoredPoints (chunks recuperados con score)
        
        Retr->>Exp: expand_hierarchy(chunks, version_id)
        Exp->>DB: Busca artículo padre en tabla chunks si vino un inciso aislado
        DB-->>Exp: Chunk del cuerpo principal del artículo
        Exp-->>Retr: Chunks contextualizados y deduplicados
        Retr-->>RAG: Lista de chunks de contexto
        
        alt Evidencia Nula o Fuera de Alcance
            RAG->>RAG: Evalúa abstención (abstained=True)
            RAG->>DB: Guarda traza de abstención
            RAG-->>API: QueryResponse (abstained=True, motivo, disclaimer)
        else Evidencia Válida Presente
            RAG->>Gen: generate_answer(query, context_chunks)
            Gen->>Gen: Construye Prompt Estricto + Directivas anti-alucinación
            Gen->>Oll: POST /api/generate (qwen2.5:7b)
            Oll-->>Gen: Texto sintético fundamentado
            Gen-->>RAG: GenerationResult(answer, disclaimer)
            
            RAG->>RAG: build_citations(context_chunks)
            Note over RAG: Las citas se extraen de los metadatos de los chunks,<br/>NUNCA del texto generado por el LLM.
            
            RAG->>DB: insert_trace(QueryTrace con latencias y citas)
            RAG-->>API: RAGResponse completa
            API-->>UI: 200 OK QueryResponse (answer, citations, disclaimer, trace_id)
            UI-->>Estudiante: Renderiza mensaje en chat, tarjetas de cita y botón "Ver en PDF"
        end
    end
```

---

## 6. Flujo de Autenticación Administrativa y Seguridad

### 6.1. Mecanismo de Autenticación Híbrido
Para conjugar la facilidad de integración en navegadores web con la automatización mediante scripts de administración, el sistema implementa tres métodos de validación simultáneos en `verify_admin_key`:
1. **Cookie HttpOnly (`admin_session`):** Emitida por el endpoint `/api/admin/login` con directivas `HttpOnly`, `SameSite=Lax` y control de expiración. Previene ataques XSS al impedir que scripts maliciosos lean el token desde JavaScript.
2. **Encabezado `X-Admin-Key`:** Utilizado en peticiones automatizadas de consola o herramientas de integración continua.
3. **Encabezado `Authorization: Bearer <token>`:** Conforme al estándar OAuth2/JWT para interoperabilidad con clientes API.

### 6.2. Protección contra Directory Traversal en Visor de PDF
El endpoint `/api/admin/versions/{version_id}/pdf` entrega el documento original confinado:
```python
# Verificación estricta de ruta canónica
allowed_dir = (Path(settings.DATA_DIR) / "pdfs").resolve()
target_path = Path(document.file_path).resolve()

if not target_path.is_relative_to(allowed_dir):
    raise HTTPException(status_code=403, detail="Acceso denegado: ruta no autorizada")
```

---

## 7. Justificación de Decisiones Tecnológicas

| Tecnología Seleccionada | Alternativas Descartadas | Justificación Técnica de la Elección |
| :--- | :--- | :--- |
| **Python 3.12 + uv** | Pipenv, Poetry, Conda | `uv` ofrece velocidades de resolución de dependencias hasta 50x superiores, bloqueo determinista (`uv.lock`) y compatibilidad nativa con entornos virtuales modernos. |
| **FastAPI** | Flask, Django REST | Rendimiento asíncrono superior (Starlette/Uvicorn), validación estricta de esquemas con Pydantic v2 y generación automática de documentación interactiva OpenAPI. |
| **Qdrant (Docker)** | ChromaDB, Pinecone, Milvus | Motor vectorial nativo en Rust de consumo ultrabajo de RAM, soporte de almacenamiento de payload en disco, persistencia simple en archivo y filtrado de metadatos estricto de altísima velocidad. |
| **Ollama Local** | LM Studio, vLLM, OpenAI API | Garantiza la soberanía del dato exigida por la normativa UTS (cero fuga a la nube); gestión de modelos simplificada por línea de comandos y consumo predecible de recursos en hardware local. |
| **Embeddings `bge-m3`** | text-embedding-ada-002, all-MiniLM | Arquitectura densa de 1024 dimensiones líder en comprensión semántica de español normativo; supera a modelos compactos en el emparejamiento de terminología jurídica y académica. |
| **LLM `qwen2.5:7b`** | Llama-3-8B, Mistral-7B, DeepSeek | Extraordinaria capacidad de seguimiento estricto de instrucciones en español (`instruction following`), mínimo índice de alucinación cuando se le provee contexto acotado y excelente razonamiento normativo. |
| **SQLite (`sqlite3`)** | PostgreSQL, MySQL | Simplicidad absoluta sin sobreingeniería: cero mantenimiento de servidores adicionales, almacenamiento en archivo único transaccional (ACID) y portabilidad completa en el repositorio. |
| **React + Vite + Tailwind** | Next.js, Angular, Vue | Empaquetado instantáneo con HMR veloz, tipado integral con TypeScript, diseño moderno y sobrio con los colores corporativos UTS (verde y dorado institucional). |

---
*Fin del Documento 02 — Paquete de Diseño del Prototipo.*
