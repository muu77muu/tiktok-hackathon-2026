import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

DEFAULTS = {
    "LLM_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
    "LLM_MODEL": "gemma-4-31b-it",
    "EMBEDDING_MODEL": "Qwen/Qwen3-Embedding-0.6B",
    "EMBEDDING_DIMENSIONS": "1024",
    "RERANKER_MODEL": "Qwen/Qwen3-Reranker-0.6B",
}

class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")

    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", DEFAULTS["LLM_BASE_URL"])
    LLM_MODEL: str = os.getenv("LLM_MODEL", DEFAULTS["LLM_MODEL"])
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
    LLM_MAX_RETRIES: int = int(os.getenv("LLM_MAX_RETRIES", "2"))

    # local HF models; DEVICE empty = auto ("cuda" if available, else "cpu")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", DEFAULTS["EMBEDDING_MODEL"])
    EMBEDDING_DIMENSIONS: int = int(
        os.getenv("EMBEDDING_DIMENSIONS", DEFAULTS["EMBEDDING_DIMENSIONS"])
    )
    EMBEDDING_DEVICE: str = os.getenv("EMBEDDING_DEVICE", "")
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", DEFAULTS["RERANKER_MODEL"])
    RERANKER_DEVICE: str = os.getenv("RERANKER_DEVICE", "")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_supabase_client():
    try:
        from supabase import create_client, Client
    except ImportError:
        raise ImportError(
            "supabase-py is not installed. "
            "Install it with: pip install supabase"
        )

    settings = get_settings()

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment variables")

    client: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )

    return client