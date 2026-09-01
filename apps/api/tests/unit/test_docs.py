from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from budgetlens.adapters.db import reset_engine
from budgetlens.config import reset_settings_cache
from budgetlens.presentation.app import create_app


def test_docs_are_enabled_in_test(client: TestClient) -> None:
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_docs_are_disabled_outside_local_and_test(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("AUTH_MODE", "oidc")
    monkeypatch.setenv("OIDC_ISSUER", "https://cognito.example/pool")
    monkeypatch.setenv("OIDC_AUDIENCE", "web-client")
    monkeypatch.setenv("OIDC_JWKS_URL", "https://cognito.example/jwks")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://budgetlens:x@localhost:5432/budgetlens",
    )
    reset_settings_cache()
    reset_engine()
    client = TestClient(create_app())
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
