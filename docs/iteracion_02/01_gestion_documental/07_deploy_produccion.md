# Guía de Despliegue y Consideraciones de Operación Local

Este documento detalla la configuración y despliegue del asistente **NORMATIVA-TG UTS** en el entorno local institucional.

---

## 1. Arquitectura de Servicios Locales

De acuerdo con las reglas no negociables del proyecto, todo el sistema se ejecuta **estrictamente de forma local**:

| Servicio | Tecnología | Puerto | Propósito |
| :--- | :--- | :---: | :--- |
| **Backend API** | FastAPI / Python 3.12 (uv) | `8000` | Motor RAG, servicio de ingestión, API administrativa y pública. |
| **Base Vectorial** | Qdrant (Docker: `normativa-qdrant`) | `6333` | Búsqueda semántica (Cosine, 1024 dims). Colección `normativa`. |
| **Base Relacional** | SQLite (`data/db/normativa.db`) | Local | Metadatos de categorías, familias, versiones, chunks y trazas. |
| **LLM & Embeddings** | Ollama (`qwen2.5:7b` / `bge-m3`) | `11434` | Inferencia generativa y generación de embeddings locales. |
| **Frontend Web** | React + Vite + Tailwind CSS | `5173` | Interfaz de usuario de chat público y panel de administración. |

---

## 2. Configuración del Entorno (`.env`)

Las variables de configuración son gestionadas de forma centralizada por `src/normativa/config.py` a través de `pydantic-settings`:

```dotenv
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b
EMBED_MODEL=bge-m3
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=normativa
SQLITE_PATH=data/db/normativa.db
DATA_DIR=data
ADMIN_API_KEY=dev-admin-secret-key
OCR_CONFIDENCE_THRESHOLD=75.0
RAG_TOP_K=5
RAG_MIN_SCORE=0.0
```

---

## 3. Puesta en Marcha Local

### 3.1. Servicios de Soporte (Docker y Ollama)
```bash
# Iniciar contenedor de Qdrant (si no está ya activo)
docker start normativa-qdrant || docker run -d --name normativa-qdrant -p 6333:6333 -v $(pwd)/data/qdrant:/qdrant/storage qdrant/qdrant:latest

# Verificar modelos locales en Ollama
ollama list
# Deben estar presentes: qwen2.5:7b y bge-m3
```

### 3.2. Backend
```bash
# Sincronizar dependencias con uv
uv sync

# Ejecutar servidor FastAPI en desarrollo
uv run uvicorn normativa.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3.3. Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## 4. Política de Respaldos

Antes de cualquier intervención sobre el corpus o el motor vectorial:
1. **SQLite**:
   ```bash
   cp data/db/normativa.db data/backups/normativa_backup_$(date +%Y%m%d_%H%M%S).db
   ```
2. **Qdrant**:
   ```bash
   curl -X POST "http://localhost:6333/collections/normativa/snapshots"
   ```
   Los snapshots de Qdrant quedan persistidos en el almacenamiento del contenedor y son recuperables directamente vía API REST de Qdrant.
