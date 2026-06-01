"""
Core configuration — single source of truth for all env vars.
Loaded once at startup via a cached singleton.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # ── GCP ───────────────────────────────────────────────────────────
    google_cloud_project: str = ""
    google_cloud_location: str = "us-central1"

    # ── Gemini ────────────────────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_max_output_tokens: int = 2048
    gemini_temperature: float = 0.2

    # ── Agent Search ──────────────────────────────────────────────────
    agent_search_engine_id: str = ""
    agent_search_location: str = "global"

    # ── Cloud SQL ─────────────────────────────────────────────────────
    cloudsql_instance_connection_name: str = ""
    cloudsql_db: str = "sparepartdb"
    cloudsql_user: str = ""
    cloudsql_password: str = ""
    cloudsql_use_proxy: bool = True
    cloudsql_proxy_host: str = "127.0.0.1"
    cloudsql_proxy_port: int = 5432

    db_pool_min: int = 2
    db_pool_max: int = 10

    # ── Agent ─────────────────────────────────────────────────────────
    agent_max_tool_calls: int = 10
    rag_top_k: int = 10

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"

    @property
    def db_dsn(self) -> str:
        """Build asyncpg DSN based on proxy vs socket mode."""
        if self.cloudsql_use_proxy:
            return (
                f"postgresql+asyncpg://{self.cloudsql_user}:{self.cloudsql_password}"
                f"@{self.cloudsql_proxy_host}:{self.cloudsql_proxy_port}/{self.cloudsql_db}"
            )
        # Cloud Run — Unix socket via Cloud SQL Connector
        socket_path = f"/cloudsql/{self.cloudsql_instance_connection_name}"
        return (
            f"postgresql+asyncpg://{self.cloudsql_user}:{self.cloudsql_password}"
            f"@/{self.cloudsql_db}?host={socket_path}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
