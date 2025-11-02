"""
Configuration module for AIWebImageService.
Loads environment variables and initializes clients.
"""
import os
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
import openai


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = Field(default="postgresql://postgres:postgres@localhost:5432/aiwebimage")

    # OpenAI
    openai_api_key: str = Field(default="")

    # Application
    env: str = Field(default="development")
    debug: bool = Field(default=True)

    # Storage
    storage_path: str = Field(default="/app/storage")

    # Image Generation
    image_provider: str = Field(default="openai")
    default_image_size: str = Field(default="1024x1024")
    default_image_quality: str = Field(default="hd")

    # Tagging
    auto_tag_enabled: bool = Field(default=True)
    min_tag_confidence: float = Field(default=0.7)
    max_tags_per_image: int = Field(default=12)

    # Vector Search
    vector_search_threshold: float = Field(default=0.7)
    vector_search_limit: int = Field(default=10)

    # API
    api_v1_prefix: str = Field(default="/api/v1")
    cors_origins: str = Field(default='["http://localhost:3000","http://localhost:8000"]')

    class Config:
        env_file = ".env"
        case_sensitive = False


# Initialize settings
settings = Settings()

# Initialize OpenAI client
if settings.openai_api_key:
    openai.api_key = settings.openai_api_key
    openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
else:
    openai_client = None
    print("WARNING: OPENAI_API_KEY not set. Image generation and tagging will not work.")


def get_openai_client() -> openai.AsyncOpenAI:
    """Get the OpenAI client instance."""
    if not openai_client:
        raise ValueError("OpenAI client not initialized. Please set OPENAI_API_KEY in .env file")
    return openai_client


# Parse CORS origins
def get_cors_origins() -> List[str]:
    """Parse CORS origins from string to list."""
    import json
    try:
        return json.loads(settings.cors_origins)
    except:
        return ["http://localhost:3000", "http://localhost:8000"]
