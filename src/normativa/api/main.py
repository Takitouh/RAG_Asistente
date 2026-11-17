from contextlib import asynccontextmanager
from fastapi import FastAPI

from normativa.api.admin import admin_router, public_versions_router
from normativa.api.query import query_router
from normativa.corpus.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Normativa TG",
    description="Asistente RAG y API de gestión del corpus normativo de la UTS",
    lifespan=lifespan,
)

app.include_router(public_versions_router)
app.include_router(admin_router)
app.include_router(query_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

