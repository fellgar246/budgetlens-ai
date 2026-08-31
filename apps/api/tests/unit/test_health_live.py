from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from budgetlens.adapters.db import reset_engine
from budgetlens.config import reset_settings_cache
from budgetlens.presentation.app import create_app


def test_live_returns_ok_without_database(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("liveness must not open a database connection")

    monkeypatch.setattr("budgetlens.adapters.db.get_engine", forbidden)
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers["x-trace-id"]


def test_live_stays_ok_when_database_url_is_unreachable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://budgetlens:x@127.0.0.1:1/budgetlens",
    )
    reset_settings_cache()
    reset_engine()
    client = TestClient(create_app())
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
