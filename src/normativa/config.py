from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    OLLAMA_BASE_URL: str = "http://localhost:11434"
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
    RAG_TOP_K: int = 5
    RAG_MIN_SCORE: float = 0.0  # 0.0 = sin filtro de umbral; ajustar en producción


settings = Settings()
