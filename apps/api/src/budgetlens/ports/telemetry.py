from __future__ import annotations

from typing import Any, Protocol


class MetricsPort(Protocol):
    def record_job_status(self, status: str, *, timed_out: bool = False) -> None: ...

    def record_ai_run(
        self,
        *,
        latency_ms: float,
        input_units: int,
        output_units: int,
        tool_calls: int,
        tool_failures: int,
    ) -> None: ...

    def record_rollback(self) -> None: ...

    def record_rate_limited(self) -> None: ...

    def snapshot(
        self,
        *,
        input_unit_cost_micros: int = 0,
        output_unit_cost_micros: int = 0,
    ) -> dict[str, Any]: ...
