from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar

T = TypeVar("T")


class ExportExecutor(Protocol):
    def run(self, operation: str, work: Callable[[], T]) -> T: ...
