from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from budgetlens.adapters.db import reset_engine
from budgetlens.config import reset_settings_cache
from budgetlens.presentation.app import create_app
from budgetlens.seed import run_seed

from .db_support import DEFAULT_DATABASE_URL, create_empty_database, drop_database

API_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def migrated_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    base_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    url, name = create_empty_database(base_url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv("DATABASE_URL", url)
    monkeypatch.setenv("LOCAL_STORAGE_PATH", str(API_ROOT / "var" / "test-storage" / name))
    reset_settings_cache()
    reset_engine()
    config = Config(str(API_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    try:
        yield url
    finally:
        reset_engine()
        reset_settings_cache()
        drop_database(base_url, name)


@pytest.fixture
def seeded_client(migrated_database: str) -> TestClient:
    del migrated_database
    run_seed()
    return TestClient(create_app())
