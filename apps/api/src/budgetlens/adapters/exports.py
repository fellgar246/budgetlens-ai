from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class InlineExportExecutor:
    def run(self, operation: str, work: Callable[[], T]) -> T:
        del operation
        return work()


class ProcessExportExecutor:
    """Same-process worker seam used by the CLI and a future background task."""

    def run(self, operation: str, work: Callable[[], T]) -> T:
        del operation
        return work()


def build_export_executor(mode: str) -> InlineExportExecutor | ProcessExportExecutor:
    if mode == "process":
        return ProcessExportExecutor()
    return InlineExportExecutor()
