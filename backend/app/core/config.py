from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # Database
    DATABASE_URL: str
    database_url: str = None  # Deprecated, use DATABASE_URL

    # Models
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    reranker_threshold: float = 0.88

    # Retrieval
    bm25_top_k: int = 20
    vector_top_k: int = 20
    rerank_top_k: int = 5

    # Redis
    redis_url: str = "redis://localhost:6379"
    redis_stream_maxlen: int = 1000  # Max entries in stream

    # Temporal
    temporal_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "jarvis-mission-notes"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Backward compatibility
        if self.database_url and not self.DATABASE_URL:
            self.DATABASE_URL = self.database_url

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
