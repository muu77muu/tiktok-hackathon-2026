import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()

DEFAULTS = {
    "LLM_BASE_URL": "https://generativelanguage.googleapis.com/v1beta/openai",
    "LLM_MODEL": "gemma-4-31b-it",
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