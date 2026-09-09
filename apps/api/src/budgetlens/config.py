from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "test", "dev", "prod"]
AuthMode = Literal["dev", "oidc"]
ObjectStorageBackend = Literal["local", "s3"]
AiProvider = Literal["stub", "bedrock"]
ImportExecutorMode = Literal["inline", "process"]
ExportExecutorMode = Literal["inline", "process"]
ConversationContentMode = Literal["full_synthetic", "redacted"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR"]


def default_env_files() -> tuple[Path, ...]:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "compose.yaml").is_file() and (parent / ".env.example").is_file():
            return (parent / ".env", Path(".env"))
    return (Path(".env"),)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=default_env_files(),
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
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_prefix: str = ""
    s3_endpoint_url: str = ""
    auth_mode: AuthMode = "dev"
    oidc_issuer: str = ""
    oidc_audience: str = ""
    oidc_jwks_url: str = ""
    oidc_jwks_cache_seconds: int = Field(default=300, ge=30)
    database_runtime_role: str = "budgetlens_app"
    storage_key_pepper: str = "budgetlens-local-storage-pepper"
    ai_provider: AiProvider = "stub"
    bedrock_region: str = "us-east-1"
    bedrock_model_id: str = ""
    ai_max_tool_calls: int = Field(default=4, ge=1)
    ai_max_context_turns: int = Field(default=12, ge=1)
    ai_max_result_rows: int = Field(default=50, ge=1)
    ai_timeout_seconds: int = Field(default=20, ge=1)
    ai_max_concurrent_conversations: int = Field(default=2, ge=1)
    import_executor: ImportExecutorMode = "inline"
    export_executor: ExportExecutorMode = "inline"
    conversation_content_mode: ConversationContentMode = "full_synthetic"
    max_upload_bytes: int = Field(default=26_214_400, ge=1)
    import_max_sheets: int = Field(default=8, ge=1)
    import_max_rows: int = Field(default=100_000, ge=1)
    import_max_columns: int = Field(default=40, ge=1)
    import_max_cells: int = Field(default=500_000, ge=1)
    cors_origins: str = "http://localhost:3000"
    db_ready_timeout_seconds: float = Field(default=2.0, gt=0)
    job_timeout_seconds: int = Field(default=600, ge=1)
    original_file_retention_days: int = Field(default=90, ge=1)
    error_report_retention_days: int = Field(default=30, ge=1)
    export_retention_hours: int = Field(default=24, ge=1)
    audit_retention_days: int = Field(default=365, ge=1)
    log_retention_days: int = Field(default=14, ge=1)
    csv_export_with_bom: bool = True
    rate_limit_upload_per_minute: int = Field(default=20, ge=1)
    rate_limit_export_per_minute: int = Field(default=20, ge=1)
    rate_limit_ai_per_minute: int = Field(default=10, ge=1)
    dependency_retry_attempts: int = Field(default=3, ge=1)
    dependency_retry_base_ms: int = Field(default=50, ge=1)
    dependency_retry_max_ms: int = Field(default=400, ge=1)
    dependency_circuit_failures: int = Field(default=5, ge=1)
    dependency_circuit_reset_seconds: int = Field(default=30, ge=1)
    ai_input_unit_cost_micros: int = Field(default=0, ge=0)
    ai_output_unit_cost_micros: int = Field(default=0, ge=0)

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
    def reject_dev_auth_outside_local_test(self) -> Self:
        if self.auth_mode == "dev" and self.app_env not in {"local", "test"}:
            raise ValueError("AUTH_MODE=dev can only be used when APP_ENV is local or test")
        if self.auth_mode == "oidc" and self.app_env in {"dev", "prod"}:
            if not (self.oidc_issuer and self.oidc_audience and self.oidc_jwks_url):
                raise ValueError(
                    "OIDC_ISSUER, OIDC_AUDIENCE and OIDC_JWKS_URL are required when AUTH_MODE=oidc"
                )
        if self.app_env not in {"local", "test"} and self.conversation_content_mode != "redacted":
            object.__setattr__(self, "conversation_content_mode", "redacted")
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
