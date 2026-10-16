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


settings = Settings()
