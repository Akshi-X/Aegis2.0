"""Application settings.

Values are read from environment variables, falling back to a repo-root .env
file. Every setting has a working default so the service boots without any
configuration at all -- useful in CI and for a fresh clone.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# .../backend/app/core/config.py -> .../backend
BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPO_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Service identity -------------------------------------------------
    project_name: str = "AEGIS-X"
    service_name: str = "aegis-x"
    version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True

    api_v1_prefix: str = "/api/v1"

    # --- PostgreSQL -------------------------------------------------------
    # Configured now; the schema itself arrives in a later phase.
    postgres_user: str = "aegis"
    postgres_password: str = "aegis"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "aegis"

    # Set this to override the assembled URL entirely (compose does exactly
    # that so the backend container can reach the `db` service by name).
    database_url: str | None = None

    # Create missing tables and apply seed data on startup. Convenient for
    # development and demos; both operations are idempotent. Turn off in any
    # environment where schema changes should be deliberate.
    auto_init_db: bool = True

    # --- Instruction parsing (LLM) ----------------------------------------
    # "auto"      -- Gemini when GEMINI_API_KEY is set, deterministic otherwise
    # "gemini"    -- force Gemini (still falls back if a call fails)
    # "heuristic" -- force the deterministic parser, never call out
    llm_provider: str = "auto"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    # Kept tight: the parser sits in a request path, and a slow model should
    # trigger the deterministic fallback rather than stall the caller.
    llm_timeout_seconds: float = 8.0

    # --- CORS -------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env file is parsed once per process."""
    return Settings()


settings = get_settings()
