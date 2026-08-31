from __future__ import annotations

import hashlib
import logging
import math
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from budgetlens.adapters.db import get_engine

ALLOWED_LOG_FIELDS = frozenset(
    {
        "timestamp",
        "level",
        "service",
        "environment",
        "event",
        "trace_id",
        "request_id",
        "organization_id_hash",
        "user_id_hash",
        "duration_ms",
        "outcome",
        "route",
        "method",
        "status_class",
        "failure_class",
    }
)
BLOCKED_LOG_KEYS = frozenset(
    {
        "password",
        "token",
        "secret",
        "authorization",
        "cookie",
        "database_url",
        "prompt",
        "content",
        "amount",
        "cells",
        "download_url",
        "presigned",
    }
)
_active_requests = 0
_active_lock = threading.Lock()


def hash_identifier(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def sanitize_log_payload(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if lowered in BLOCKED_LOG_KEYS or lowered not in ALLOWED_LOG_FIELDS:
            continue
        if value is None:
            continue
        cleaned[key] = value
    return cleaned


def classify_failure(*, status_code: int | None = None, dependency: str | None = None) -> str:
    if dependency:
        return "dependency"
    if status_code is not None and status_code >= 500:
        return "application"
    return "infrastructure"


def status_class(status_code: int) -> str:
    return f"{status_code // 100}xx"


@dataclass
class _MetricSeries:
    count: int = 0
    error_count: int = 0
    total_ms: float = 0.0
    samples_ms: list[float] = field(default_factory=list[float])

    def observe(self, duration_ms: float, *, error: bool) -> None:
        self.count += 1
        self.total_ms += duration_ms
        self.samples_ms.append(duration_ms)
        if len(self.samples_ms) > 512:
            self.samples_ms = self.samples_ms[-256:]
        if error:
            self.error_count += 1

    def percentile(self, ratio: float) -> float | None:
        if not self.samples_ms:
            return None
        ordered = sorted(self.samples_ms)
        index = min(len(ordered) - 1, max(0, math.ceil(len(ordered) * ratio) - 1))
        return round(ordered[index], 2)


class MetricsRegistry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[tuple[str, str, str], _MetricSeries] = defaultdict(_MetricSeries)
        self._jobs_timed_out = 0
        self._jobs_by_status: dict[str, int] = defaultdict(int)
        self._ai_runs = 0
        self._ai_tool_calls = 0
        self._ai_tool_failures = 0
        self._ai_input_units = 0
        self._ai_output_units = 0
        self._ai_latency_ms = _MetricSeries()
        self._rollbacks = 0
        self._rate_limited = 0

    def record_request(
        self,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        key = (method, route, status_class(status_code))
        with self._lock:
            self._requests[key].observe(duration_ms, error=status_code >= 500)

    def record_job_status(self, status: str, *, timed_out: bool = False) -> None:
        with self._lock:
            self._jobs_by_status[status] += 1
            if timed_out:
                self._jobs_timed_out += 1

    def record_ai_run(
        self,
        *,
        latency_ms: float,
        input_units: int,
        output_units: int,
        tool_calls: int,
        tool_failures: int,
    ) -> None:
        with self._lock:
            self._ai_runs += 1
            self._ai_tool_calls += tool_calls
            self._ai_tool_failures += tool_failures
            self._ai_input_units += input_units
            self._ai_output_units += output_units
            self._ai_latency_ms.observe(latency_ms, error=tool_failures > 0)

    def record_rollback(self) -> None:
        with self._lock:
            self._rollbacks += 1

    def record_rate_limited(self) -> None:
        with self._lock:
            self._rate_limited += 1

    def snapshot(
        self,
        *,
        input_unit_cost_micros: int = 0,
        output_unit_cost_micros: int = 0,
    ) -> dict[str, Any]:
        with self._lock:
            requests = [
                {
                    "method": method,
                    "route": route,
                    "status_class": klass,
                    "count": series.count,
                    "errors": series.error_count,
                    "duration_ms_p95": series.percentile(0.95),
                }
                for (method, route, klass), series in sorted(self._requests.items())
            ]
            jobs = {
                "timed_out": self._jobs_timed_out,
                "by_status": dict(self._jobs_by_status),
            }
            estimated_cost = None
            if input_unit_cost_micros or output_unit_cost_micros:
                micros = (
                    self._ai_input_units * input_unit_cost_micros
                    + self._ai_output_units * output_unit_cost_micros
                )
                estimated_cost = {
                    "currency": "USD",
                    "amount": f"{micros / 1_000_000:.6f}",
                    "estimate": True,
                }
            ai = {
                "runs": self._ai_runs,
                "tool_calls": self._ai_tool_calls,
                "tool_failures": self._ai_tool_failures,
                "latency_ms_p95": self._ai_latency_ms.percentile(0.95),
                "estimated_cost": estimated_cost,
            }
            rollbacks = self._rollbacks
            rate_limited = self._rate_limited
        pool = _pool_snapshot()
        with _active_lock:
            active = _active_requests
        return {
            "requests": requests,
            "active_requests": active,
            "db_pool": pool,
            "db_rollbacks": rollbacks,
            "jobs": jobs,
            "ai": ai,
            "rate_limited": rate_limited,
        }


_metrics = MetricsRegistry()


def metrics_registry() -> MetricsRegistry:
    return _metrics


def reset_metrics() -> None:
    global _metrics
    _metrics = MetricsRegistry()


def begin_request() -> None:
    global _active_requests
    with _active_lock:
        _active_requests += 1


def end_request() -> None:
    global _active_requests
    with _active_lock:
        _active_requests = max(0, _active_requests - 1)


def _pool_snapshot() -> dict[str, int]:
    try:
        pool = get_engine().pool
    except Exception:
        return {"checked_out": 0, "overflow": 0, "size": 0}
    checked_out = int(getattr(pool, "checkedout", lambda: 0)())
    overflow = int(getattr(pool, "overflow", lambda: 0)())
    size = int(getattr(pool, "size", lambda: 0)())
    return {"checked_out": checked_out, "overflow": overflow, "size": size}


def bind_log_record(record: logging.LogRecord, extra: dict[str, Any]) -> None:
    for key, value in extra.items():
        if key in ALLOWED_LOG_FIELDS:
            setattr(record, key, value)
