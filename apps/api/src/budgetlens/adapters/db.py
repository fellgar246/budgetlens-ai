from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from budgetlens.config import Settings, get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def _connect_args(settings: Settings) -> dict[str, object]:
    timeout = max(1, int(settings.db_ready_timeout_seconds))
    return {"connect_timeout": timeout}


def get_engine(settings: Settings | None = None) -> Engine:
    global _engine, _session_factory
    if _engine is None:
        resolved = settings or get_settings()
        _engine = create_engine(
            resolved.database_url,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=5,
            connect_args=_connect_args(resolved),
        )
        event.listen(_engine, "before_cursor_execute", _before_cursor_execute)
        event.listen(_engine, "after_cursor_execute", _after_cursor_execute)
        _session_factory = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def _before_cursor_execute(
    _conn: object,
    _cursor: object,
    _statement: str,
    _parameters: object,
    context: Any,
    _executemany: bool,
) -> None:
    context._budgetlens_query_started = time.perf_counter()


def _after_cursor_execute(
    _conn: object,
    _cursor: object,
    statement: str,
    _parameters: object,
    context: Any,
    _executemany: bool,
) -> None:
    started = getattr(context, "_budgetlens_query_started", None)
    if not isinstance(started, float):
        return
    from budgetlens.observability import logical_query_name, metrics_registry

    metrics_registry().record_query(
        logical_query_name(statement),
        (time.perf_counter() - started) * 1000,
    )


def get_session_factory() -> sessionmaker[Session]:
    if _session_factory is None:
        get_engine()
    assert _session_factory is not None
    return _session_factory


def reset_engine() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def ping_database() -> bool:
    try:
        with session_scope() as session:
            session.execute(text("SELECT 1"))
    except Exception:
        return False
    return True
