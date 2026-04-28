from __future__ import annotations

from datetime import date
from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Auditable Business Metrics Copilot"
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173"]
    database_url: str = "postgresql+psycopg2://postgres:postgres@db:5432/metrics"
    database_connect_retries: int = 12
    database_connect_retry_seconds: float = 2.0
    default_data_source_label: str = "mock_database"
    fallback_row_limit: int = 200
    fixed_today: date | None = None
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def today(self) -> date:
        return self.fixed_today or date.today()


@lru_cache
def get_settings() -> Settings:
    return Settings()

