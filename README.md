# NORMATIVA-TG UTS — Asistente Inteligente RAG y Gestión Normativa
## Proyecto de Grado: Desarrollo Tecnológico (Formato F-DC-124 / F-DC-125)

Prototipo académico desarrollado para la consulta inteligente, fundamentada y orientativa del **Reglamento de Trabajo de Grado** de las **Unidades Tecnológicas de Santander (UTS)** (Acuerdo del Consejo Directivo No. 01-021 de 2019).

El sistema opera de forma **100% local y soberana** (sin consumo de APIs externas ni servicios en la nube), utilizando:
- **FastAPI** (Python 3.12, tipado con Pydantic v2 y gestor `uv`).
- **React + Vite + Tailwind CSS** (Frontend web interactivo y panel administrativo).
- **Qdrant** (Base de datos vectorial en Docker con almacenamiento en disco).
- **Ollama** (Modelos locales: generativo `qwen2.5:7b` y embeddings `bge-m3`).
- **SQLite** (`data/db/normativa.db`, metadatos, chunks estructurados y trazas de auditoría).

---

## 1. Documentación Final de Entrega Técnica (`docs/entrega_final/`)

Todos los entregables técnicos, especificaciones de ingeniería, informes de validación y evidencias visuales exigidos académicamente se encuentran consolidados en la carpeta [`docs/entrega_final/`](docs/entrega_final/):

| Documento | Descripción y Contenido Principal |
| :--- | :--- |
| **[01_analisis_y_especificacion.md](docs/entrega_final/01_analisis_y_especificacion.md)** | Análisis normativo, usuarios, RF, RNF, seguridad, casos de uso y matriz de trazabilidad integral. |
| **[02_paquete_diseno.md](docs/entrega_final/02_paquete_diseno.md)** | Arquitectura completa, diagramas de componentes, modelo relacional SQLite, colección Qdrant y secuencia RAG. |
| **[03_informe_procesamiento_ocr.md](docs/entrega_final/03_informe_procesamiento_ocr.md)** | Informe definitivo de extracción y OCR (19 págs., 91.71% confianza, 181 chunks, corrección Art. 1). |
| **[04_informe_validacion_tecnica.md](docs/entrega_final/04_informe_validacion_tecnica.md)** | Evaluación técnica exhaustiva del banco de 30 consultas normativas con Ollama y Qdrant en caliente. |
| **[05_validacion_versionamiento.md](docs/entrega_final/05_validacion_versionamiento.md)** | Prueba formal de coexistencia, aislamiento de versiones y conmutación en caliente sin mezcla de fuentes. |
| **[06_pruebas_funcionales_seguridad.md](docs/entrega_final/06_pruebas_funcionales_seguridad.md)** | Auditoría de seguridad (cookies HttpOnly, path traversal) y resultados de 107 pruebas (83 backend / 24 frontend). |
| **[07_manual_tecnico.md](docs/entrega_final/07_manual_tecnico.md)** | Manual técnico reproducible: requisitos, instalación, endpoints REST, respaldos y recuperación de desastres. |
| **[08_manual_usuario.md](docs/entrega_final/08_manual_usuario.md)** | Manual para estudiantes, docentes y administradores: uso del chat, interpretación de citas, visor PDF y panel admin. |
| **[09_documentacion_despliegue.md](docs/entrega_final/09_documentacion_despliegue.md)** | Guía de despliegue local, topología de red, puertos, script de arranque y protocolo de sustentación. |
| **[10_informe_consolidado_fdc125.md](docs/entrega_final/10_informe_consolidado_fdc125.md)** | Síntesis consolidada según las 4 fases del F-DC-124 como insumo directo para el informe final de grado F-DC-125. |
| **[resultados_30_preguntas.json](docs/entrega_final/resultados_30_preguntas.json)** | Dataset íntegro con respuestas, chunks, puntuaciones, citas, trazas y juicios evaluativos en JSON. |
| **[resultados_30_preguntas.csv](docs/entrega_final/resultados_30_preguntas.csv)** | Dataset tabular consolidado para análisis cuantitativo y métricas en hojas de cálculo. |
| **[evidencias/](docs/entrega_final/evidencias/)** | Carpeta con folios renderizados del PDF oficial a 150 DPI y exportación de trazas de auditoría. |

---

## 2. Requisitos Previos del Sistema

- **Sistema Operativo:** Linux (Ubuntu 22.04 LTS o superior recomendado), macOS o Windows con WSL2.
- **Python 3.12** y gestor [`uv`](https://docs.astral.sh/uv/) instalado.
- **Node.js 18+** y `npm`.
- **Docker Engine y Docker Compose** (para el contenedor de Qdrant).
- **Tesseract OCR:** Paquetes `tesseract-ocr` y `tesseract-ocr-spa`.
- **Ollama Local** instalado con los modelos descargados:
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

## 4. Puesta en Marcha de Servicios Locales

### Paso 1: Iniciar Qdrant Vector DB
```bash
docker compose up -d
```

### Paso 2: Iniciar Servidor Ollama
```bash
ollama serve
```

### Paso 3: Iniciar Backend FastAPI
```bash
uv run uvicorn normativa.api.main:app --host 0.0.0.0 --port 8000 --reload
```
- Documentación OpenAPI interactiva: `http://localhost:8000/docs`
- Verificación de salud: `http://localhost:8000/health`

### Paso 4: Iniciar Frontend Web (Vite)
En otra terminal:
```bash
cd frontend
npm run dev -- --host 0.0.0.0 --port 5173
```
- Aplicación web accesible en: `http://localhost:5173`
- Panel administrativo en: `http://localhost:5173/admin` (Clave: `dev-admin-secret-key`)

---

## 5. Ejecución de Pruebas Automatizadas

El proyecto cuenta con un 100% de éxito en sus suites de aseguramiento de calidad:

### Backend (83 pruebas unitarias y de integración con Pytest):
```bash
uv run pytest -v
```

### Frontend (24 pruebas de componentes, autenticación y contratos con Vitest):
```bash
cd frontend
npm test
cd ..
```

### Ejecución Reproducible del Banco de 30 Preguntas RAG:
```bash
uv run python scripts/ejecutar_30_preguntas.py
```

---

## 6. Reglas No Negociables del Proyecto (Auditoría Técnica)

1. **Estructura Conservada:** Cada chunk conserva capítulo, artículo, parágrafo, inciso, página, documento y versión.
2. **Aislamiento Estricto:** Toda búsqueda vectorial filtra obligatoriamente por `version_id`; nunca se mezclan normativas.
3. **Citas Deterministas:** Las citas se construyen a partir de los metadatos de los chunks recuperados, **nunca** desde texto alucinado por el LLM.
4. **Abstención Activa:** Si la evidencia es insuficiente o la consulta es ajena al reglamento, el sistema se abstiene (`abstained: true`).
5. **Trazabilidad Total:** Cada consulta registra una traza persistente en la tabla `traces` de SQLite con UUID y métricas de latencia.
6. **Carácter Orientativo:** El asistente incluye advertencias de que no emite actos administrativos vinculantes.
7. **Cero Dependencias Cloud:** 100% soberano, gratuito y reproducible localmente.

---
*Unidades Tecnológicas de Santander (UTS) — 2026*
