from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from budgetlens.adapters.db import reset_engine
from budgetlens.config import reset_settings_cache
from budgetlens.presentation.app import create_app


def test_ready_returns_503_when_database_is_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://budgetlens:x@127.0.0.1:1/budgetlens",
    )
    reset_settings_cache()
    reset_engine()
    client = TestClient(create_app())
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "unavailable"
    assert body["components"] == {"database": "error"}
    assert "x-trace-id" in response.headers
