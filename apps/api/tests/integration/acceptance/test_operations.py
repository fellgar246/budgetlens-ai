from __future__ import annotations

import os
import time
from pathlib import Path
from urllib.parse import urlparse

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, text

from budgetlens.adapters.db import reset_engine
from budgetlens.config import reset_settings_cache
from budgetlens.dev_identities import ALPHA_ADMIN_ID, ALPHA_ORG_ID, BETA_ORG_ID
from budgetlens.presentation.app import create_app
from tests.integration.acceptance.support import PREFIX, auth_headers, entry_count
from tests.integration.db_support import DEFAULT_DATABASE_URL, drop_database, with_database_name

API_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = API_ROOT.parents[1]


def _database_name(url: str) -> str:
    parsed = urlparse(url.replace("postgresql+psycopg://", "postgresql://", 1))
    return parsed.path.lstrip("/")


def test_migrated_stack_is_ready_and_at_head(migrated_database: str) -> None:
    client = TestClient(create_app())
    live = client.get(f"{PREFIX}/health/live")
    ready = client.get(f"{PREFIX}/health/ready")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready", "components": {"database": "ok"}}
    config = Config(str(API_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    heads = script.get_heads()
    assert len(heads) == 1
    engine = create_engine(migrated_database)
    with engine.connect() as connection:
        current = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
        tables = set(inspect(connection).get_table_names())
    engine.dispose()
    assert current == heads[0]
    assert {"organizations", "financial_entries", "import_jobs"}.issubset(tables)


def test_readiness_fails_fast_when_database_is_down_and_liveness_stays_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_MODE", "dev")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://budgetlens:x@127.0.0.1:1/budgetlens",
    )
    monkeypatch.setenv("DB_READY_TIMEOUT_SECONDS", "1")
    reset_settings_cache()
    reset_engine()
    client = TestClient(create_app())
    started = time.perf_counter()
    ready = client.get(f"{PREFIX}/health/ready")
    elapsed = time.perf_counter() - started
    assert ready.status_code == 503
    assert ready.json()["status"] == "unavailable"
    assert elapsed < 3
    live = client.get(f"{PREFIX}/health/live")
    assert live.status_code == 200
    assert live.json()["status"] == "ok"


def test_empty_and_n_minus_one_databases_reach_head(monkeypatch: pytest.MonkeyPatch) -> None:
    from tests.integration.db_support import create_empty_database

    base_url = os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)
    url, name = create_empty_database(base_url)
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", url)
    reset_settings_cache()
    reset_engine()
    config = Config(str(API_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
    engine.dispose()
    assert "schema_meta" in tables
    drop_database(base_url, name)

    url, name = create_empty_database(base_url)
    monkeypatch.setenv("DATABASE_URL", url)
    reset_settings_cache()
    reset_engine()
    script = ScriptDirectory.from_config(config)
    n_minus_one = script.get_revision(script.get_heads()[0]).down_revision
    assert isinstance(n_minus_one, str)
    command.upgrade(config, n_minus_one)
    engine = create_engine(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO schema_meta (key, value) "
                "VALUES ('kept', 'yes') ON CONFLICT (key) DO NOTHING"
            )
        )
    engine.dispose()
    command.upgrade(config, "head")
    engine = create_engine(url)
    with engine.connect() as connection:
        value = connection.execute(
            text("SELECT value FROM schema_meta WHERE key = 'kept'")
        ).scalar_one()
    engine.dispose()
    drop_database(base_url, name)
    reset_engine()
    assert value == "yes"


def test_application_rollback_keeps_the_previous_image_without_schema_downgrade() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8")
    operations = (REPO_ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
    assert "budgetlens-api:previous" in makefile
    assert "budgetlens-web:previous" in makefile
    assert "docker tag budgetlens-api:previous" in operations
    assert "Do not roll back to an incompatible schema" in operations
    script = REPO_ROOT / "scripts" / "acceptance-rollback.sh"
    assert script.is_file()


def test_isolated_restore_preserves_counts_and_tenant_invariants(
    seeded_client: TestClient, migrated_database: str
) -> None:
    alpha_accounts = seeded_client.get(
        f"{PREFIX}/accounts",
        headers=auth_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    )
    assert alpha_accounts.status_code == 200
    expected = {
        "alpha_accounts": len(alpha_accounts.json()["items"]),
        "alpha_entries": entry_count(organization_id=ALPHA_ORG_ID),
        "beta_entries": entry_count(organization_id=BETA_ORG_ID),
    }
    source_name = _database_name(migrated_database)
    dest_name = f"budgetlens_restore_{source_name[-8:]}"
    reset_engine()
    admin_url = with_database_name(
        os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL), "budgetlens"
    )
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = :name AND pid <> pg_backend_pid()"
                ),
                {"name": source_name},
            )
            connection.execute(text(f'CREATE DATABASE "{dest_name}" TEMPLATE "{source_name}"'))
    finally:
        engine.dispose()
    dest_url = with_database_name(migrated_database, dest_name)
    cloned = create_engine(dest_url)
    try:
        with cloned.connect() as connection:
            alpha = connection.execute(
                text("SELECT count(*) FROM accounts WHERE organization_id = :org"),
                {"org": str(ALPHA_ORG_ID)},
            ).scalar_one()
            beta_in_alpha = connection.execute(
                text(
                    "SELECT count(*) FROM financial_entries "
                    "WHERE organization_id = :alpha AND organization_id = :beta"
                ),
                {"alpha": str(ALPHA_ORG_ID), "beta": str(BETA_ORG_ID)},
            ).scalar_one()
            alpha_entries = connection.execute(
                text("SELECT count(*) FROM financial_entries WHERE organization_id = :org"),
                {"org": str(ALPHA_ORG_ID)},
            ).scalar_one()
            beta_entries = connection.execute(
                text("SELECT count(*) FROM financial_entries WHERE organization_id = :org"),
                {"org": str(BETA_ORG_ID)},
            ).scalar_one()
        assert alpha == expected["alpha_accounts"]
        assert alpha_entries == expected["alpha_entries"]
        assert beta_entries == expected["beta_entries"]
        assert beta_in_alpha == 0
    finally:
        cloned.dispose()
        drop_database(os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL), dest_name)
