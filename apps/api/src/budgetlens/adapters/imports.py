from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class InlineImportExecutor:
    def run(self, operation: str, work: Callable[[], T]) -> T:
        del operation
        return work()


class ProcessImportExecutor:
    """Same-process worker seam used by the CLI and a future ECS task."""

    def run(self, operation: str, work: Callable[[], T]) -> T:
        del operation
        return work()


def build_import_executor(mode: str) -> InlineImportExecutor | ProcessImportExecutor:
    if mode == "process":
        return ProcessImportExecutor()
    return InlineImportExecutor()
