from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4


class Clock(Protocol):
    def now(self) -> datetime: ...


class IdFactory(Protocol):
    def new_id(self) -> UUID: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class Uuid4Factory:
    def new_id(self) -> UUID:
        return uuid4()


class FrozenClock:
    def __init__(self, instant: datetime) -> None:
        self._instant = instant if instant.tzinfo is not None else instant.replace(tzinfo=UTC)

    def now(self) -> datetime:
        return self._instant


class SequentialIdFactory:
    def __init__(self, start: int = 1) -> None:
        self._next = start

    def new_id(self) -> UUID:
        value = self._next
        self._next += 1
        return UUID(int=value)
