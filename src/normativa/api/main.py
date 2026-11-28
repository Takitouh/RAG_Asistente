import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from normativa.api.admin import admin_router, public_versions_router
from normativa.api.query import query_router
from normativa.corpus.db import init_db

# Ruta al frontend compilado.
# En producción (Docker) el paquete se instala en site-packages, así que
# __file__ NO apunta al directorio del proyecto.  Usamos FRONTEND_DIR env
# o la ruta fija de producción /app/frontend/dist como primera opción,
# y la ruta relativa a __file__ como fallback para desarrollo local.
def _resolve_frontend_dir() -> Path:
    env = os.getenv("FRONTEND_DIR")
    if env:
        return Path(env)
    # Ruta fija de producción (Dockerfile copia dist aquí)
    prod = Path("/app/frontend/dist")
    if prod.is_dir():
        return prod
    # Fallback: desarrollo local (src/normativa/api/main.py → ../../../../frontend/dist)
    return Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "dist"

_FRONTEND_DIR = _resolve_frontend_dir()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Normativa TG",
    description="Asistente RAG y API de gestión del corpus normativo de la UTS",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(public_versions_router)
app.include_router(admin_router)
app.include_router(query_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# ---------- Servir frontend estático en producción ----------
# Solo se monta si el directorio dist/ existe (no afecta desarrollo con Vite).
if _FRONTEND_DIR.is_dir():
    # Montar assets estáticos (JS, CSS, imágenes)
    app.mount("/assets", StaticFiles(directory=_FRONTEND_DIR / "assets"), name="static-assets")

    # Catch-all: cualquier ruta no-API sirve index.html (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Sirve el index.html del frontend para habilitar client-side routing."""
        file_path = _FRONTEND_DIR / full_path
        if full_path and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(_FRONTEND_DIR / "index.html")

