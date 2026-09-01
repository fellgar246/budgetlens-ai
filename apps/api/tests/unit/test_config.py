from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from budgetlens.config import Settings, default_env_files

REPO_ROOT = Path(__file__).resolve().parents[4]
ENV_EXAMPLE = REPO_ROOT / ".env.example"
REQUIRED_INITIAL_VARS = (
    "APP_ENV",
    "APP_LOG_LEVEL",
    "DATABASE_URL",
    "OBJECT_STORAGE_BACKEND",
    "LOCAL_STORAGE_PATH",
    "AUTH_MODE",
    "AI_PROVIDER",
    "BEDROCK_REGION",
    "BEDROCK_MODEL_ID",
    "AI_MAX_TOOL_CALLS",
    "AI_TIMEOUT_SECONDS",
    "MAX_UPLOAD_BYTES",
)


def test_valid_settings_normalize_driver() -> None:
    settings = Settings.model_validate(
        {
            "app_env": "local",
            "database_url": "postgresql://budgetlens:local@localhost:5432/budgetlens",
        }
    )
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.docs_enabled is True


def test_blank_database_url_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"database_url": "   "})


def test_unsupported_database_scheme_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate({"database_url": "mysql://localhost/budgetlens"})


def test_prod_rejects_dev_auth() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "app_env": "prod",
                "auth_mode": "dev",
                "database_url": "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
            }
        )


def test_dev_env_rejects_dev_auth() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "app_env": "dev",
                "auth_mode": "dev",
                "database_url": "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
            }
        )


def test_prod_accepts_oidc() -> None:
    settings = Settings.model_validate(
        {
            "app_env": "prod",
            "auth_mode": "oidc",
            "database_url": "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
            "oidc_issuer": "https://cognito.example/pool",
            "oidc_audience": "web-client",
            "oidc_jwks_url": "https://cognito.example/jwks",
        }
    )
    assert settings.docs_enabled is False
    assert settings.cors_origin_list == ["http://localhost:3000"]
    assert settings.conversation_content_mode == "redacted"


def test_local_keeps_full_synthetic_conversation_content() -> None:
    settings = Settings.model_validate(
        {
            "app_env": "local",
            "database_url": "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
        }
    )
    assert settings.conversation_content_mode == "full_synthetic"


def _docs_block_for(text: str, env_name: str) -> str:
    match = re.search(rf"^{env_name}=", text, re.MULTILINE)
    if match is None:
        return ""
    return text[: match.start()].rsplit("\n\n", 1)[-1]


def test_env_example_documents_every_setting() -> None:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing: list[str] = []
    for field_name in Settings.model_fields:
        env_name = field_name.upper()
        block = _docs_block_for(text, env_name)
        if not block:
            missing.append(env_name)
            continue
        for token in ("Type:", "Secret:", "Applies:"):
            if token not in block:
                missing.append(f"{env_name} missing {token}")
    assert missing == []


def test_default_env_files_include_the_repository_root() -> None:
    files = default_env_files()
    assert files[0] == REPO_ROOT / ".env"
    assert Path(".env") in files


def test_env_example_includes_initial_variables() -> None:
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    missing = [name for name in REQUIRED_INITIAL_VARS if name not in text]
    assert missing == []


def test_env_file_overrides_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_LOG_LEVEL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_LOG_LEVEL=DEBUG\nDATABASE_URL=postgresql+psycopg://file:file@localhost/file\n",
        encoding="utf-8",
    )
    settings = Settings(_env_file=str(env_file))  # pyright: ignore[reportCallIssue]
    assert settings.app_log_level == "DEBUG"
    assert "file:file" in settings.database_url


def test_process_environment_overrides_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_LOG_LEVEL=DEBUG\nDATABASE_URL=postgresql+psycopg://file:file@localhost/file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("APP_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://env:env@localhost/env")
    settings = Settings(_env_file=str(env_file))  # pyright: ignore[reportCallIssue]
    assert settings.app_log_level == "WARNING"
    assert "env:env" in settings.database_url
