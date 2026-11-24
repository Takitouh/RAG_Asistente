# Manual Técnico del Sistema NORMATIVA-TG UTS
## Guía Integral de Instalación, Operación, Mantenimiento y Recuperación
**Proyecto:** NORMATIVA-TG UTS (F-DC-124 / F-DC-125)  
**Institución:** Unidades Tecnológicas de Santander (UTS)  
**Fecha de consolidación:** Noviembre de 2026  
**Perfil de Audiencia:** Ingenieros de Software, Administradores de Sistemas, Coordinadores de TI  

---

## 1. Descripción General y Arquitectura

**NORMATIVA-TG UTS** es una plataforma de software académico diseñada para resolver consultas en lenguaje natural sobre el Reglamento de Trabajo de Grado de las Unidades Tecnológicas de Santander. 

El sistema implementa una arquitectura **RAG (Retrieval-Augmented Generation)** estrictamente local que combina:
- **Base de datos vectorial:** Qdrant (en contenedor Docker, persistencia en disco).
- **Servidor de Modelos de Inteligencia Artificial:** Ollama (ejecutando localmente el modelo generativo `qwen2.5:7b` y el modelo de incrustaciones densas `bge-m3`).
- **Base de datos relacional y de auditoría:** SQLite 3 nativo (`data/db/normativa.db`).
- **Backend de Servicios REST:** FastAPI (Python 3.12, tipado Pydantic v2).
- **Frontend Web Interactivo:** React 18, Vite, TypeScript y Tailwind CSS.

---

## 2. Estructura del Repositorio de Código

```text
FastAPIProject2/
├── .bin/                        # Binarios auxiliares locales (ej. gestor uv)
├── data/                        # Datos y almacenamiento local persistente
│   ├── db/                      # Base de datos relacional SQLite
│   │   └── normativa.db         # Tablas: documents, versions, chunks, traces
│   ├── pdfs/                    # Archivos PDF originales confinados
│   ├── processed/               # Informes de extracción, logs de limpieza y JSONs
│   └── qdrant/                  # Almacenamiento físico del contenedor Qdrant
├── docs/                        # Documentación técnica del proyecto
│   └── entrega_final/           # Entregables técnicos formales y evidencias F-DC-125
│       ├── diagramas/           # Fuentes de diagramas arquitectónicos
│       ├── evidencias/          # Capturas reales de interfaces y comandos
│       ├── 01_analisis_y_especificacion.md
│       ├── 02_paquete_diseno.md
│       ├── 03_informe_procesamiento_ocr.md
│       ├── 04_informe_validacion_tecnica.md
│       ├── 05_validacion_versionamiento.md
│       ├── 06_pruebas_funcionales_seguridad.md
│       ├── 07_manual_tecnico.md
│       ├── 08_manual_usuario.md
│       ├── 09_documentacion_despliegue.md
│       ├── 10_informe_consolidado_fdc125.md
│       ├── resultados_30_preguntas.json
│       └── resultados_30_preguntas.csv
├── frontend/                    # Aplicación cliente web React
│   ├── src/                     # Código fuente TypeScript y componentes
│   ├── package.json             # Dependencias Node.js y scripts de build
│   └── vite.config.ts           # Configuración de empaquetado y proxy de desarrollo
├── scripts/                     # Scripts utilitarios y de automatización
│   ├── check_env.py             # Diagnóstico de recursos, Ollama y Qdrant
│   ├── parse_pdf.py             # Procesamiento manual de PDFs por consola
│   └── ejecutar_30_preguntas.py # Script de evaluación técnica del banco RAG
├── src/normativa/               # Backend en Python (paquete modular)
│   ├── api/                     # Routers públicos y administrativos
│   ├── corpus/                  # SQLite, modelos relacionales y chunker jerárquico
│   ├── generation/              # Generador RAG, citas deterministas y abstención
│   ├── ingestion/               # Extractor híbrido, Tesseract OCR, cleaner y parser
│   ├── retrieval/               # Indexador y recuperador con filtro de versión
│   ├── tracing/                 # Registro y consulta de trazas de auditoría
│   └── config.py                # Ajustes centralizados mediante pydantic-settings
├── tests/                       # Pruebas automatizadas de backend con pytest
├── docker-compose.yml           # Definición de servicio local de Qdrant
├── pyproject.toml               # Configuración de dependencias Python
└── README.md                    # Guía rápida de referencia institucional
```

---

## 3. Requisitos de Infraestructura (Hardware y Software)

### 3.1. Requisitos de Hardware
- **Procesador (CPU):** Mínimo 4 núcleos x86_64 o ARM64 (recomendado 8 núcleos o superior).
- **Memoria RAM:** Mínimo 16 GB de RAM (para soportar simultáneamente el sistema operativo, Qdrant y la carga del modelo de 7B en memoria).
- **Almacenamiento:** Mínimo 20 GB de espacio libre en disco de estado sólido (SSD NVMe recomendado).
- **Aceleración Gráfica (Opcional pero muy recomendada):** GPU NVIDIA con al menos 6 GB a 8 GB de VRAM (soporte CUDA) o GPU Apple Silicon con memoria unificada. En CPU pura la inferencia es funcional pero la latencia por respuesta aumenta a 30-50 segundos.

### 3.2. Requisitos de Software
- **Sistema Operativo:** Linux (Ubuntu 22.04 LTS / Debian 12 o superior recomendado), macOS o Windows 11 con WSL2.
- **Python:** Versión 3.12 (gestionado mediante `uv` v0.5+).
- **Node.js:** Versión 18 LTS o 20 LTS (con gestor `npm`).
- **Docker Engine y Docker Compose:** Para la ejecución de Qdrant.
- **Tesseract OCR:** Paquete del sistema con datos del idioma español (`tesseract-ocr` y `tesseract-ocr-spa`).
- **Ollama:** Versión 0.3+ instalada en el sistema anfitrión.

---

## 4. Procedimiento de Instalación Paso a Paso

### 4.1. Instalación de Dependencias del Sistema (Linux Debian/Ubuntu)
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-spa poppler-utils curl git
```

### 4.2. Instalación de Ollama y Descarga de Modelos Locales
1. Instalar Ollama:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```
2. Descargar los modelos requeridos:
   ```bash
   ollama pull qwen2.5:7b
   ollama pull bge-m3
   ```
3. Verificar modelos disponibles:
   ```bash
   ollama list
   ```

### 4.3. Arranque de la Base de Datos Vectorial (Qdrant)
El servicio se define en `docker-compose.yml`:
```bash
docker compose up -d
```
Verificar que responda en el puerto 6333:
```bash
curl http://localhost:6333/collections
```

### 4.4. Instalación de Dependencias del Backend (Python / uv)
El proyecto utiliza el gestor de paquetes de alto rendimiento `uv`:
```bash
# Sincronizar el entorno virtual determinista
uv sync
```

### 4.5. Instalación y Compilación del Frontend (React)
```bash
cd frontend
npm install
npm run build
cd ..
```

---

## 5. Configuración de Variables de Entorno

El archivo `.env` en la raíz del proyecto define los parámetros de ejecución:

```env
# Conectividad con Ollama Local
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b
EMBED_MODEL=bge-m3

# Conectividad con Qdrant Vector DB
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=normativa

# Almacenamiento Relacional y Archivos
SQLITE_PATH=data/db/normativa.db
DATA_DIR=data

# Seguridad y Autenticación Administrativa
ADMIN_API_KEY=dev-admin-secret-key

# Umbrales Heurísticos
OCR_CONFIDENCE_THRESHOLD=75.0
RAG_TOP_K=5
RAG_MIN_SCORE=0.0
```

---

## 6. Puesta en Marcha de los Servicios del Sistema

### Terminal 1: Servidor Ollama (si no corre como servicio de sistema)
```bash
ollama serve
```

### Terminal 2: Backend FastAPI
```bash
uv run uvicorn normativa.api.main:app --host 0.0.0.0 --port 8000 --reload
```
- Documentación OpenAPI interactiva (Swagger UI): `http://localhost:8000/docs`
- Verificación de salud: `http://localhost:8000/health`

### Terminal 3: Frontend Web Vite
```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```
- Interfaz web accesible en: `http://localhost:5173`

---

## 7. Referencia de la API REST del Sistema

### 7.1. Endpoints Públicos
- `GET /health`: Estado del servicio (`{"status": "ok"}`).
- `GET /api/versions/active`: Consulta la versión normativa global actualmente activa en el sistema.
- `POST /api/query`: Endpoint principal de consulta RAG.
  - **Entrada JSON:** `{"query": "¿Cuáles son las modalidades de grado?"}`
  - **Salida JSON:** `QueryResponse` con respuesta sintética, citas estructuradas, estado de abstención, disclaimer y latencia.

### 7.2. Endpoints Administrativos (Requieren Autenticación)
- `POST /api/admin/login`: Autentica credenciales administrativas y emite la cookie `admin_session`.
- `POST /api/admin/logout`: Invalida la sesión administrativa.
- `GET /api/admin/stats`: Métricas de control (versiones registradas, chunks, trazas).
- `GET /api/admin/versions`: Lista completa de versiones normativas en la base de datos.
- `POST /api/admin/versions/upload`: Carga multipart/form-data de un archivo PDF oficial.
- `POST /api/admin/versions/{version_id}/process`: Inicia el pipeline de extracción, OCR y vectorización.
- `POST /api/admin/versions/{version_id}/review`: Registra la revisión humana (`approve` o `reject`).
- `POST /api/admin/versions/{version_id}/activate`: Activa en caliente una versión como normativa global activa.
- `GET /api/admin/versions/{version_id}/pdf`: Entrega el binario PDF confinado para visualización.
- `GET /api/admin/traces`: Consulta las trazas históricas de auditoría del sistema.

---

## 8. Mantenimiento, Respaldos y Recuperación de Desastres

### 8.1. Respaldo de la Base de Datos SQLite y PDFs
Para salvaguardar la base de datos relacional y los documentos originales:
```bash
# Crear directorio de respaldo con marca de tiempo
BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# Respaldo transaccional de SQLite
uv run python -c "
import sqlite3
src = sqlite3.connect('data/db/normativa.db')
dst = sqlite3.connect('$BACKUP_DIR/normativa.db')
src.backup(dst)
dst.close()
src.close()
"

# Respaldo de los archivos PDF oficiales
cp -r data/pdfs "$BACKUP_DIR/"
echo "Respaldo completado en $BACKUP_DIR"
```

### 8.2. Respaldo y Restauración de Qdrant
Los datos vectoriales residen en `data/qdrant/`. Dado que el contenedor mapea el volumen `./data/qdrant:/qdrant/storage`, un respaldo del directorio conserva el índice:
```bash
# Detener temporalmente el contenedor para evitar escrituras sucias
docker compose stop
tar -czvf "$BACKUP_DIR/qdrant_backup.tar.gz" data/qdrant/
docker compose start
```

### 8.3. Procedimiento de Reconstrucción del Índice Vectorial
Si la base de datos Qdrant se corrompe o se pierde el volumen:
1. Eliminar la carpeta dañada y reiniciar Qdrant:
   ```bash
   docker compose down -v
   docker compose up -d
   ```
2. Reejecutar el script de indexación sobre la versión registrada:
   ```bash
   uv run python -c "
   from normativa.corpus.service import CorpusService
   service = CorpusService()
   service.process_and_index_version('uts_tg_2019', force_ocr=True)
   print('Índice reconstruido exitosamente.')
   "
   ```

---

## 9. Solución de Problemas Frecuentes (Troubleshooting)

| Síntoma / Error | Causa Probable | Solución Técnica Comprobada |
| :--- | :--- | :--- |
| **HTTP 503: "No se pudo conectar con Ollama"** | El servicio de Ollama no se encuentra en ejecución o fue detenido. | Ejecutar `ollama serve` en una terminal y verificar `curl http://localhost:11434/api/tags`. |
| **HTTP 503: "Fallo de conexión con Qdrant"** | El contenedor Docker de Qdrant no está iniciado. | Ejecutar `docker compose up -d` y verificar con `docker ps`. |
| **El chat indica: "Sin normativa activa"** | Ninguna versión tiene el campo `is_active = 1` en SQLite. | Acceder a `/admin`, ubicar la versión `uts_tg_2019` y presionar el botón **Activar**, o invocar `POST /api/admin/versions/uts_tg_2019/activate`. |
| **Respuesta muy lenta (> 60 segundos)** | La inferencia de `qwen2.5:7b` se está ejecutando sobre CPU sin aceleración. | Verificar que Ollama detecte la GPU (`nvidia-smi`), o reducir `RAG_TOP_K` a 3 para disminuir el tamaño del prompt. |
| **Error en extracción: "TesseractNotFound"** | El paquete `tesseract-ocr` no está instalado en el sistema operativo anfitrión. | Instalar mediante `sudo apt-get install tesseract-ocr tesseract-ocr-spa`. |

---
*Fin del Documento 07 — Manual Técnico del Sistema.*
