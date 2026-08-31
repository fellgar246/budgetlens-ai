from __future__ import annotations

import uuid
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, text

DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://budgetlens:budgetlens_local_only@127.0.0.1:5433/budgetlens"
)


def with_database_name(url: str, name: str) -> str:
    normalized = url.replace("postgresql+psycopg://", "postgresql://", 1)
    parsed = urlparse(normalized)
    replaced = parsed._replace(path=f"/{name}")
    return "postgresql+psycopg://" + urlunparse(replaced).removeprefix("postgresql://")


def create_empty_database(base_url: str) -> tuple[str, str]:
    name = f"budgetlens_it_{uuid.uuid4().hex[:8]}"
    admin_url = with_database_name(base_url, "budgetlens")
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.execute(text(f'CREATE DATABASE "{name}"'))
    except Exception as exc:
        raise RuntimeError("PostgreSQL is required for integration tests") from exc
    finally:
        engine.dispose()
    return with_database_name(base_url, name), name


def drop_database(base_url: str, name: str) -> None:
    admin_url = with_database_name(base_url, "budgetlens")
    engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    finally:
        engine.dispose()
