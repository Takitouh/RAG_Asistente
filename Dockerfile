# ============================================================
# NORMATIVA-TG UTS — Dockerfile monolítico (Backend + Frontend)
# ============================================================
# Multi-stage build:
#   1) Compilar frontend React con Node
#   2) Instalar dependencias Python con uv
#   3) Imagen final ligera con la app lista para producción
#
# Build:  docker build -t normativa-tg .
# Run:    docker compose -f docker-compose.prod.yml up -d --build
# ============================================================

# ---- Stage 1: Build Frontend ----
FROM node:20-alpine AS frontend-builder

WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build


# ---- Stage 2: Install Python dependencies ----
FROM python:3.12-slim AS python-builder

# Instalar uv (gestor de paquetes Python)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /build
COPY pyproject.toml uv.lock* ./
COPY src/ ./src/

# Crear virtualenv e instalar dependencias (sin dev)
RUN uv venv /opt/venv && \
    VIRTUAL_ENV=/opt/venv uv pip install --no-cache .


# ---- Stage 3: Runtime ----
FROM python:3.12-slim AS runtime

LABEL maintainer="UTS - Proyecto de Grado NORMATIVA-TG"
LABEL description="Asistente RAG monolítico para consulta del Reglamento de Trabajo de Grado"

# Dependencias del sistema para pytesseract / OCR
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-spa \
        libgl1 \
        libglib2.0-0 \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Copiar virtualenv instalado
COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Usuario no-root para seguridad en producción
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /app

# Copiar código fuente del backend
COPY --chown=appuser:appuser src/ ./src/

# Copiar frontend compilado
COPY --from=frontend-builder --chown=appuser:appuser /build/frontend/dist ./frontend/dist

# Crear directorios de datos persistentes
RUN mkdir -p /app/data/db /app/data/pdfs /app/data/qdrant && \
    chown -R appuser:appuser /app/data

# Variables de entorno con valores por defecto para producción
# (se sobreescriben con docker-compose o -e)
ENV OLLAMA_BASE_URL="http://ollama:11434"
ENV QDRANT_URL="http://qdrant:6333"
ENV SQLITE_PATH="/app/data/db/normativa.db"
ENV DATA_DIR="/app/data"

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "normativa.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
