from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from budgetlens.config import Settings
from budgetlens.presentation.app import create_app


def test_create_app_rejects_dev_auth_in_prod() -> None:
    with pytest.raises(ValidationError):
        Settings.model_validate(
            {
                "app_env": "prod",
                "auth_mode": "dev",
                "database_url": "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
            }
        )


def test_oidc_mode_does_not_serve_dev_identities(
    env_settings: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    del env_settings
    monkeypatch.setenv("AUTH_MODE", "oidc")
    from budgetlens.adapters.db import reset_engine
    from budgetlens.config import reset_settings_cache

    reset_settings_cache()
    reset_engine()
    client = TestClient(create_app())
    response = client.get("/api/v1/dev/identities")
    assert response.status_code == 404
    me = client.get(
        "/api/v1/me",
        headers={"Authorization": "Bearer 11111111-1111-4111-8111-111111111111"},
    )
    assert me.status_code == 401
