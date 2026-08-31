from __future__ import annotations

import pytest
from pydantic import ValidationError

from budgetlens.config import Settings


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


def test_prod_accepts_oidc() -> None:
    settings = Settings.model_validate(
        {
            "app_env": "prod",
            "auth_mode": "oidc",
            "database_url": "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
        }
    )
    assert settings.docs_enabled is False
    assert settings.cors_origin_list == ["http://localhost:3000"]
