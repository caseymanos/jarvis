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
    REDIS_URL: str = "redis://localhost:6379"
    redis_url: str = None  # Deprecated, use REDIS_URL
    REDIS_STREAM_MAXLEN: int = 1000  # Max entries in stream
    redis_stream_maxlen: int = None  # Deprecated, use REDIS_STREAM_MAXLEN

    # Temporal
    TEMPORAL_HOST: str = "localhost:7233"
    temporal_host: str = None  # Deprecated, use TEMPORAL_HOST
    TEMPORAL_NAMESPACE: str = "default"
    temporal_namespace: str = None  # Deprecated, use TEMPORAL_NAMESPACE
    TEMPORAL_TASK_QUEUE: str = "jarvis-mission-notes"
    temporal_task_queue: str = None  # Deprecated, use TEMPORAL_TASK_QUEUE

    # Speech-to-Text (Whisper)
    OPENAI_API_KEY: str
    STT_MODEL: str = "whisper-1"
    STT_LANGUAGE: str = "en"

    # Language Model (LLM)
    LLM_PROVIDER: str = "openai"  # xai, openai, openrouter, anthropic
    XAI_API_KEY: str = ""
    OPENROUTER_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o"  # Default to GPT-4o
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 1000

    # Text-to-Speech
    TTS_PROVIDER: str = "openai"  # openai, elevenlabs
    TTS_MODEL: str = "tts-1"
    TTS_VOICE: str = "nova"  # alloy, echo, fable, onyx, nova, shimmer
    ELEVENLABS_API_KEY: str = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Backward compatibility
        if self.database_url and not self.DATABASE_URL:
            self.DATABASE_URL = self.database_url
        if self.redis_url and not self.REDIS_URL:
            self.REDIS_URL = self.redis_url
        if self.redis_stream_maxlen and not self.REDIS_STREAM_MAXLEN:
            self.REDIS_STREAM_MAXLEN = self.redis_stream_maxlen
        if self.temporal_host and not self.TEMPORAL_HOST:
            self.TEMPORAL_HOST = self.temporal_host
        if self.temporal_namespace and not self.TEMPORAL_NAMESPACE:
            self.TEMPORAL_NAMESPACE = self.temporal_namespace
        if self.temporal_task_queue and not self.TEMPORAL_TASK_QUEUE:
            self.TEMPORAL_TASK_QUEUE = self.temporal_task_queue

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Global settings instance for backwards compatibility
settings = get_settings()
