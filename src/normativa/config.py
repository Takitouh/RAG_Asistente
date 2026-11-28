from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_PROVIDER: str = "ollama"
    LLM_TIMEOUT_SECONDS: float = Field(default=120.0, gt=0)
    LLM_MODEL: str = "qwen2.5:7b"
    EMBED_MODEL: str = "bge-m3"
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "normativa"
    SQLITE_PATH: str = "data/db/normativa.db"
    DATA_DIR: str = "data"
    ADMIN_API_KEY: str = "dev-admin-secret-key"

    # Umbral de confianza OCR (heurístico, no garantía de exactitud textual)
    OCR_CONFIDENCE_THRESHOLD: float = 75.0

    # Parámetros de recuperación RAG
    RAG_TOP_K: int = Field(default=5, ge=1)
    RAG_MAX_CONTEXT_CHUNKS: int = Field(default=14, ge=1)
    RAG_CONTEXT_TOKENS: int = Field(default=10240, ge=4096, le=32768)
    RAG_OUTPUT_TOKENS: int = Field(default=1400, ge=1)
    RAG_TEMPLATE_RESERVE_TOKENS: int = Field(default=256, ge=64)
    RAG_TOKEN_ESTIMATION: Literal["bytes", "qwen2"] = "qwen2"
    RAG_EXPANSION_UNITS: int = Field(default=2, ge=0)
    RAG_MAX_EXPANDED_CHUNKS: int | None = Field(default=12, ge=0)
    RAG_MIN_SCORE: float = 0.0  # 0.0 = sin filtro de umbral; ajustar en producción


settings = Settings()
