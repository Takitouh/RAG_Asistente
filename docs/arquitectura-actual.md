# Arquitectura actual

Volver al [índice de documentación](README.md). Para el alcance y los límites,
consulte el [estado actual](estado-actual.md).

## Flujo implementado

```text
PDF oficial
  -> extractor (capa de texto u OCR en español)
  -> PageText + líneas con posición normalizada
  -> cleaner (encabezados, pies, índice y ruido)
  -> CleanPage
  -> parser
  -> ParsedDocument + informes JSON, Markdown y texto
```

El comando `scripts/parse_pdf.py` materializa este flujo y guarda sus salidas
en `data/processed/`. Puede reutilizar el caché `*_pages.json`; `--no-cache`
fuerza una nueva extracción.

## Módulos

| Ruta | Responsabilidad actual |
| --- | --- |
| `src/normativa/api/main.py` | Crea FastAPI con título `Normativa TG` y expone `GET /health`. |
| `src/normativa/config.py` | Carga URL de Ollama y Qdrant, modelos, colección, SQLite y directorio de datos. |
| `src/normativa/ollama_utils.py` | Compara nombres de modelos de Ollama y detecta modelos ausentes. |
| `src/normativa/ingestion/extractor.py` | Extrae texto y líneas; cambia a OCR si hay menos de 50 caracteres o se fuerza OCR. |
| `src/normativa/ingestion/cleaner.py` | Detecta repetición posicional para remover encabezados/pies; retira índice y ruido. |
| `src/normativa/ingestion/parser.py` | Reconstruye estructura normativa, repara ciertas lecturas OCR por secuencia y genera vistas e informes. |
| `src/normativa/ingestion/models.py` | Define las estructuras inmutables del documento procesado. |
| `scripts/inspect_pdf.py` | Genera muestra, texto crudo completo y reporte de inspección para un PDF. |
| `scripts/parse_pdf.py` | Ejecuta extracción, limpieza y parseo; escribe los resultados procesados. |
| `scripts/check_env.py` | Comprueba recursos locales, Qdrant y Ollama. |

Los paquetes `corpus`, `generation`, `retrieval` y `tracing` existen, pero sus
archivos `__init__.py` no tienen implementación funcional todavía.

## Metadatos que conserva el parseo

Cada `Articulo` contiene tipo (`reglamento` o `acuerdo`), número u ordinal,
capítulo (número romano, número normalizado y título), texto, parágrafos,
incisos, rango de páginas, confianza OCR media y flags. Cada `Paragrafo` e
`Inciso` conserva su identificador y texto.

Esto satisface parcialmente la necesidad de preservar estructura y página para
la futura indexación. Aún faltan `documento`, `version_id` y el modelo de chunk
que obligue dichos campos; por ello estos objetos no deben considerarse todavía
evidencia apta para respuesta o cita. Véase [Pendientes y brechas](pendientes-y-brechas.md).

## Servicios y almacenamiento locales

- Qdrant se declara en `docker-compose.yml`, con datos persistidos en
  `data/qdrant` y puerto `6333`.
- Ollama se asume local en `http://localhost:11434`.
- La ruta SQLite configurada por defecto es `data/db/normativa.db`, pero no hay
  código que la inicialice o la use.
- Los PDFs y productos de procesamiento viven bajo `data/`, carpeta ignorada
  por Git para evitar versionar datos locales.

La configuración exacta y cómo verificar estos servicios están documentadas en
[Operación y verificación](operacion-y-verificacion.md).
