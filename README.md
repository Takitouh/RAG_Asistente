# NORMATIVA-TG UTS — Asistente Inteligente RAG y Gestión Normativa

Prototipo académico basado en el documento **F-DC-124** para la consulta del Reglamento de Trabajo de Grado de las **Unidades Tecnológicas de Santander (UTS)**.

El sistema funciona de forma 100% local, utilizando **FastAPI**, **React + Vite + Tailwind CSS**, **Qdrant** (base de datos vectorial), **Ollama** (modelo LLM `qwen2.5:7b` y embeddings `bge-m3`), y **SQLite** (metadatos, chunks y trazas de auditoría).

---

## 1. Arquitectura del Repositorio

```text
FastAPIProject2/
├── src/normativa/               # Backend FastAPI y lógica RAG
│   ├── api/                     # Routers públicos y administrativos
│   ├── corpus/                  # SQLite, modelos y chunker normativo
│   ├── ingestion/               # Extracción, OCR, limpieza y parseo
│   ├── retrieval/               # Indexador y recuperador en Qdrant
│   ├── generation/              # Generador RAG, citas y abstención
│   └── tracing/                 # Trazabilidad de consultas en SQLite
├── frontend/                    # Aplicación web React + TypeScript
│   ├── src/
│   │   ├── api/                 # Cliente HTTP y contratos
│   │   ├── components/          # Chat, citas, panel admin, modales
│   │   ├── hooks/               # useChat, useActiveVersion, useAdminAuth
│   │   ├── pages/               # ChatPage, AdminLoginPage, AdminDashboardPage
│   │   └── types/               # Tipos TypeScript compartidos
│   ├── package.json
│   ├── vite.config.ts
│   └── ...
├── data/                        # Almacenamiento local (PDFs, SQLite, Qdrant)
├── tests/                       # Pruebas automatizadas pytest backend
├── pyproject.toml               # Dependencias Python (uv)
└── README.md
```

---

## 2. Requisitos Previos

- **Python 3.12+** y gestor [`uv`](https://docs.astral.sh/uv/)
- **Node.js 18+** y `npm`
- **Docker** y Docker Compose (para Qdrant)
- **Ollama** instalado localmente con los modelos:
  ```bash
  ollama pull qwen2.5:7b
  ollama pull bge-m3
  ```

---

## 3. Instalación de Dependencias

### Backend (Python / uv)
```bash
uv sync
```

### Frontend (Node / npm)
```bash
cd frontend
npm install
cd ..
```

---

## 4. Variables de Entorno

Copie el archivo de ejemplo si no existe `.env`:
```bash
cp .env.example .env
```

Variables disponibles en `.env`:
```env
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
```

---

## 5. Puesta en Marcha de Servicios

### Paso 1: Iniciar Qdrant y Ollama
```bash
# Iniciar base de datos vectorial Qdrant
docker compose up -d

# Verificar que Ollama esté sirviendo
ollama serve
```

### Paso 2: Iniciar Backend FastAPI
```bash
uv run uvicorn normativa.api.main:app --host 0.0.0.0 --port 8000 --reload
```
La documentación interactiva OpenAPI estará en `http://localhost:8000/docs`.

### Paso 3: Iniciar Frontend Vite
En otra terminal:
```bash
cd frontend
npm run dev
```
La interfaz web estará accesible en `http://localhost:5173`.

---

## 6. Guía de Uso del Sistema

### 6.1. Chat Normativo Público (`http://localhost:5173/`)
- Muestra el reglamento oficial actualmente activo y los metadatos normativos.
- Permite formular preguntas en lenguaje natural sobre modalidades de grado, requisitos, causales de reprobación, etc.
- Presenta citas estructuradas deterministas con el texto oficial del chunk y visor de la página correspondiente del PDF original.
- Si no hay evidencia suficiente en la versión activa, emite una abstención explícita (`abstained: true`) sin alucinaciones.

### 6.2. Panel Administrativo (`http://localhost:5173/admin`)
1. **Autenticación**: Ingrese en `/admin/login` utilizando la clave administrativa (`ADMIN_API_KEY`, por defecto `dev-admin-secret-key`). La sesión se gestiona con cookie segura y token.
2. **Dashboard**: Consulta de métricas reales (versiones registradas, chunks en Qdrant, trazas de auditoría).
3. **Cargar Normativa**: Formulario para cargar un nuevo archivo PDF del reglamento, registrando nombre, año, número de acuerdo y activando la extracción/indexación automática.
4. **Auditoría OCR y Validación**: Revisión de páginas procesadas, herramienta OCR, anomalías estructurales y contraste con el PDF original.
5. **Aprobación y Activación**: Un administrador puede aprobar versiones pendientes de revisión y activar una versión con un solo clic. El chat pasa a responder exclusivamente con dicha versión activa.

---

## 7. Ejecución de Pruebas Automatizadas

### Backend (66 pruebas con pytest)
```bash
uv run pytest -v
```

### Frontend (14 pruebas con Vitest)
```bash
cd frontend
npm test
cd ..
```

### Compilación y Verificación de Tipos Frontend
```bash
cd frontend
npm run build
cd ..
```

---

## 8. Resolución de Problemas Comunes

- **Backend 503 / "No se pudo conectar con Ollama o Qdrant"**:
  Verifique que Qdrant esté corriendo en el puerto 6333 (`docker ps`) y Ollama en el puerto 11434 (`curl http://localhost:11434/api/tags`).
- **"Sin reglamento activo en el chat"**:
  Ingrese al panel de administración `/admin`, ubique el reglamento deseado y presione **Activar**.
- **CORS o Proxy**:
  Vite redirige automáticamente las peticiones `/api` a `http://localhost:8000`. Si consume FastAPI directamente, el middleware CORS permite los puertos 5173 y 3000 con credenciales activas.
- **Acceso a PDF con Error 403 / 404**:
  El backend valida que el archivo se encuentre confinado dentro de `data/pdfs/` para impedir cualquier ataque de path traversal.
