from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from budgetlens.adapters.db import reset_engine
from budgetlens.application.rate_limit import limiter
from budgetlens.config import reset_settings_cache
from budgetlens.observability import reset_metrics
from budgetlens.presentation.app import create_app
from budgetlens.runtime import reset_runtime

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://budgetlens:budgetlens_local_only@127.0.0.1:5433/budgetlens"
)


@pytest.fixture(autouse=True)
def isolate_rate_limits() -> Iterator[None]:
    limiter().reset()
    yield
    limiter().reset()


@pytest.fixture
def env_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv(
        "DATABASE_URL",
        os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
    )
    monkeypatch.setenv("APP_VERSION", "0.1.0")
    monkeypatch.setenv("GIT_SHA", "testsha")
    monkeypatch.setenv("BUILD_TIME", "2026-08-31T00:00:00Z")
    reset_settings_cache()
    reset_engine()
    reset_metrics()
    reset_runtime()
    limiter().reset()
    yield
    reset_settings_cache()
    reset_engine()
    reset_metrics()
    reset_runtime()
    limiter().reset()


@pytest.fixture
def client(env_settings: None) -> TestClient:
    return TestClient(create_app())
