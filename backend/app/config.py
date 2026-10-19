from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite://"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-insecure-change-me"
    jwt_expire_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:3000"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "documents"
    minio_secure: bool = False

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "research_chunks"

    max_pdf_bytes: int = 20 * 1024 * 1024
    max_pdf_pages: int = 80

    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    llm_model: str = "Qwen/Qwen2.5-1.5B-Instruct"

    storage_backend: str = "memory"
    queue_backend: str = "noop"
    vector_backend: str = "memory"
    embedding_backend: str = "hash"
    llm_backend: str = "stub"

    prompt_version: str = "cited-qa-v1"
    retrieval_version: str = "bge-small-top8-v1"
    retrieval_top_k: int = 8
    llm_generation_timeout_seconds: int = 120

    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


def reset_settings() -> None:
    get_settings.cache_clear()
