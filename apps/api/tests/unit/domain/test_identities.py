from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from budgetlens.domain.identities import (
    FrozenClock,
    SequentialIdFactory,
    SystemClock,
    Uuid4Factory,
    format_rfc3339,
)


def test_system_clock_is_timezone_aware_utc() -> None:
    instant = SystemClock().now()
    offset = instant.utcoffset()
    assert instant.tzinfo is not None
    assert offset is not None
    assert offset.total_seconds() == 0


def test_frozen_clock_and_sequential_ids_are_injectable() -> None:
    clock = FrozenClock(datetime(2026, 4, 1, 12, 0, 0))
    ids = SequentialIdFactory(start=7)
    assert clock.now().tzinfo is UTC
    assert clock.now() == datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC)
    assert ids.new_id() == UUID(int=7)
    assert ids.new_id() == UUID(int=8)


def test_uuid_factory_uses_version_four() -> None:
    generated = Uuid4Factory().new_id()
    assert generated.version == 4


def test_rfc3339_uses_utc() -> None:
    instant = datetime(2026, 1, 15, 8, 30, tzinfo=UTC)
    assert format_rfc3339(instant) == "2026-01-15T08:30:00Z"
