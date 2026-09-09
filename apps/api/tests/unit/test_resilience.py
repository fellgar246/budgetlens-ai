from __future__ import annotations

import pytest

from budgetlens.application.resilience import (
    CircuitBreaker,
    RetryPolicy,
    is_transient_dependency_error,
    reset_circuits,
    retry_with_jitter,
)
from budgetlens.domain.errors import CircuitOpenError, NotFoundError, ValidationError
from budgetlens.observability import metrics_registry, reset_metrics


def test_retry_with_jitter_retries_transient_errors() -> None:
    calls = {"count": 0}
    sleeps: list[float] = []

    def boom() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise TimeoutError("timeout")
        return "ok"

    result = retry_with_jitter(
        boom,
        policy=RetryPolicy(attempts=3, base_seconds=0.05, max_seconds=0.4),
        sleeper=sleeps.append,
        rng=lambda: 1.0,
    )
    assert result == "ok"
    assert calls["count"] == 3
    assert sleeps == [0.05, 0.1]


def test_retry_with_jitter_does_not_retry_validation() -> None:
    calls = {"count": 0}

    def boom() -> None:
        calls["count"] += 1
        raise ValidationError("INVALID", "no")

    with pytest.raises(ValidationError):
        retry_with_jitter(boom, policy=RetryPolicy(attempts=4), sleeper=lambda _: None)
    assert calls["count"] == 1


def test_circuit_opens_after_threshold_and_records_metric() -> None:
    reset_metrics()
    reset_circuits()
    clock = {"now": 0.0}
    breaker = CircuitBreaker(
        "ai",
        failure_threshold=2,
        reset_seconds=10,
        clock=lambda: clock["now"],
    )

    def fail() -> None:
        raise TimeoutError("timeout")

    with pytest.raises(TimeoutError):
        breaker.call(fail)
    with pytest.raises(TimeoutError):
        breaker.call(fail)
    with pytest.raises(CircuitOpenError) as exc:
        breaker.call(lambda: "unused")
    assert exc.value.code == "AI_UNAVAILABLE"
    assert exc.value.retryable is True
    assert metrics_registry().snapshot()["ai"]["circuit_open"] == 1
    clock["now"] = 11
    assert breaker.call(lambda: "recovered") == "recovered"
    reset_metrics()


def test_transient_classifier() -> None:
    assert is_transient_dependency_error(TimeoutError("x")) is True
    assert is_transient_dependency_error(RuntimeError("throttling from provider")) is True
    assert is_transient_dependency_error(NotFoundError()) is False
    assert is_transient_dependency_error(CircuitOpenError("ai")) is False
