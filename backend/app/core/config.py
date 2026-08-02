from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Code Learn Assist API"
    environment: str = "development"
    database_url: str | None = None
    redis_url: str | None = None
    yandex_gpt_endpoint: str | None = None
    yandex_gpt_api_key: str | None = None
    yandex_gpt_model: str | None = None
    yandex_gpt_timeout_seconds: float = Field(default=20, ge=1, le=60)
    prompt_version: str = "python-library-practice-v3"
    max_generation_attempts: int = Field(default=3, ge=1, le=5)
    generation_lock_ttl_seconds: int = Field(default=60, ge=10, le=300)
    cache_ttl_seconds: int = Field(default=86400, ge=60)

    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
