from __future__ import annotations

from functools import lru_cache

from pydantic import AnyUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Motly API"
    app_env: str = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/motly"

    supabase_url: AnyUrl | None = None
    supabase_jwt_issuer: str | None = None
    supabase_jwt_audience: str = "authenticated"
    supabase_jwks_url: AnyUrl | None = None

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"

    quiz_max_questions: int = Field(default=15, ge=1, le=15)
    quiz_context_chars: int = Field(default=24000, ge=2000, le=60000)
    quiz_generation_timeout_seconds: int = Field(default=90, ge=10, le=300)
    quiz_generation_max_attempts: int = Field(default=2, ge=1, le=5)
    quiz_worker_poll_seconds: float = Field(default=2, ge=0.5, le=60)

    backend_cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
