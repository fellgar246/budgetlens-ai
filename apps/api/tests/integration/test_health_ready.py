from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from budgetlens.adapters.db import reset_engine
from budgetlens.config import reset_settings_cache
from budgetlens.presentation.app import create_app

from .db_support import DEFAULT_DATABASE_URL, create_empty_database, drop_database

API_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def migrated_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    base_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    url, name = create_empty_database(base_url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", url)
    reset_settings_cache()
    reset_engine()
    config = Config(str(API_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    try:
        yield url
    finally:
        reset_engine()
        drop_database(base_url, name)


@pytest.mark.integration
def test_ready_returns_200_when_database_is_available(migrated_database: str) -> None:
    del migrated_database
    client = TestClient(create_app())
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "components": {"database": "ok"}}


@pytest.mark.integration
def test_upgrade_from_empty_database_creates_schema_meta(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    with engine.connect() as connection:
        value = connection.execute(
            text("SELECT value FROM schema_meta WHERE key = 'app_name'")
        ).scalar_one()
    engine.dispose()
    assert value == "budgetlens"
