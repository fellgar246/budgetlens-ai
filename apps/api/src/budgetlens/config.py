from __future__ import annotations

from functools import lru_cache
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "test", "dev", "prod"]
AuthMode = Literal["dev", "oidc"]
ObjectStorageBackend = Literal["local", "s3"]
AiProvider = Literal["stub", "bedrock"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: AppEnv = "local"
    app_log_level: LogLevel = "INFO"
    app_version: str = "0.1.0"
    git_sha: str = "unknown"
    build_time: str = "unknown"
    database_url: str
    object_storage_backend: ObjectStorageBackend = "local"
    local_storage_path: str = "./var/storage"
    auth_mode: AuthMode = "dev"
    ai_provider: AiProvider = "stub"
    bedrock_region: str = "us-east-1"
    bedrock_model_id: str = ""
    ai_max_tool_calls: int = Field(default=4, ge=1)
    ai_timeout_seconds: int = Field(default=20, ge=1)
    max_upload_bytes: int = Field(default=26_214_400, ge=1)
    cors_origins: str = "http://localhost:3000"
    db_ready_timeout_seconds: float = Field(default=2.0, gt=0)

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("DATABASE_URL is required")
        if cleaned.startswith("postgresql://"):
            return "postgresql+psycopg://" + cleaned.removeprefix("postgresql://")
        if cleaned.startswith("postgresql+psycopg://"):
            return cleaned
        raise ValueError("DATABASE_URL must use postgresql:// or postgresql+psycopg://")

    @field_validator("app_log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, value: object) -> object:
        if isinstance(value, str):
            return value.upper()
        return value

    @model_validator(mode="after")
    def reject_dev_auth_in_prod(self) -> Self:
        if self.app_env == "prod" and self.auth_mode == "dev":
            raise ValueError("AUTH_MODE=dev cannot be used when APP_ENV=prod")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def docs_enabled(self) -> bool:
        return self.app_env in {"local", "test"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]


def reset_settings_cache() -> None:
    get_settings.cache_clear()
