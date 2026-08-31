from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from budgetlens.adapters.db import reset_engine
from budgetlens.config import reset_settings_cache

from .db_support import DEFAULT_DATABASE_URL, create_empty_database, drop_database

API_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.integration
def test_upgrade_from_empty_creates_domain_tables(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    engine.dispose()
    assert {
        "schema_meta",
        "users",
        "organizations",
        "memberships",
        "accounts",
        "departments",
        "cost_centers",
        "budget_versions",
        "audit_events",
        "idempotency_records",
    }.issubset(tables)


@pytest.mark.integration
def test_upgrade_from_n_minus_one_preserves_schema_meta(monkeypatch: pytest.MonkeyPatch) -> None:
    base_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    url, name = create_empty_database(base_url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", url)
    reset_settings_cache()
    reset_engine()
    config = Config(str(API_ROOT / "alembic.ini"))
    command.upgrade(config, "20260831_0001")
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO schema_meta (key, value) "
                "VALUES ('kept', 'yes') ON CONFLICT (key) DO NOTHING"
            )
        )
        tables = inspect(connection).get_table_names()
        assert "users" not in tables
    engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.connect() as connection:
        value = connection.execute(
            text("SELECT value FROM schema_meta WHERE key = 'kept'")
        ).scalar_one()
        tables = inspect(connection).get_table_names()
    engine.dispose()
    reset_engine()
    drop_database(base_url, name)
    assert value == "yes"
    assert "budget_versions" in tables
