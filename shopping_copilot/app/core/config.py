import os
from functools import lru_cache

from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv()


class Settings:
    """Application settings and configuration."""
    
    # Supabase Configuration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_KEY", "")
    
    # App Configuration
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def get_supabase_client():
    """Initialize and return Supabase client."""
    try:
        from supabase import create_client, Client
    except ImportError:
        raise ImportError(
            "supabase-py is not installed. "
            "Install it with: pip install supabase"
        )
    
    settings = get_settings()
    
    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_KEY must be set in environment variables"
        )
    
    client: Client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY
    )
    
    return client
