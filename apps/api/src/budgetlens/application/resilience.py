from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from budgetlens.domain.errors import (
    CircuitOpenError,
    DependencyUnavailableError,
    NotFoundError,
    ValidationError,
)
from budgetlens.observability import metrics_registry

Sleeper = Callable[[float], None]
Rng = Callable[[], float]


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    attempts: int = 3
    base_seconds: float = 0.05
    max_seconds: float = 0.4


class CircuitBreaker:
    def __init__(
        self,
        name: str,
        *,
        failure_threshold: int = 5,
        reset_seconds: float = 30.0,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_seconds = reset_seconds
        self._clock = clock or time.monotonic
        self._lock = threading.Lock()
        self._failures = 0
        self._opened_at: float | None = None
        self._state = "closed"

    def reset(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None
            self._state = "closed"

    def call[T](self, operation: Callable[[], T]) -> T:
        now = self._clock()
        with self._lock:
            if self._state == "open":
                opened_at = now if self._opened_at is None else self._opened_at
                if now - opened_at >= self.reset_seconds:
                    self._state = "half_open"
                else:
                    metrics_registry().record_circuit_open()
                    raise CircuitOpenError(self.name)
        try:
            result = operation()
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result

    def _record_success(self) -> None:
        with self._lock:
            self._failures = 0
            self._opened_at = None
            self._state = "closed"

    def _record_failure(self) -> None:
        with self._lock:
            self._failures += 1
            if self._state == "half_open" or self._failures >= self.failure_threshold:
                self._state = "open"
                self._opened_at = self._clock()


def retry_with_jitter[T](
    operation: Callable[[], T],
    *,
    policy: RetryPolicy | None = None,
    retryable: Callable[[BaseException], bool] | None = None,
    sleeper: Sleeper | None = None,
    rng: Rng | None = None,
) -> T:
    resolved = policy or RetryPolicy()
    decide = retryable or is_transient_dependency_error
    sleep = sleeper or time.sleep
    random_fn = rng or random.random
    last: BaseException | None = None
    attempts = max(1, resolved.attempts)
    for attempt in range(attempts):
        try:
            return operation()
        except BaseException as exc:
            last = exc
            if not decide(exc) or attempt >= attempts - 1:
                raise
            delay = min(resolved.max_seconds, resolved.base_seconds * (2**attempt))
            sleep(delay * (0.5 + 0.5 * random_fn()))
    assert last is not None
    raise last


def is_transient_dependency_error(exc: BaseException) -> bool:
    if isinstance(exc, CircuitOpenError):
        return False
    if isinstance(exc, NotFoundError | ValidationError | DependencyUnavailableError):
        return False
    if isinstance(exc, TimeoutError | ConnectionError | OSError):
        return True
    text = str(exc).lower()
    markers = (
        "timeout",
        "throttl",
        "temporar",
        "unavailable",
        "reset",
        "busy",
        "too many requests",
        "service unavailable",
        "503",
        "429",
    )
    return any(marker in text for marker in markers)


def policy_from_settings(settings: object | None) -> RetryPolicy:
    attempts = getattr(settings, "dependency_retry_attempts", 3)
    base_ms = getattr(settings, "dependency_retry_base_ms", 50)
    max_ms = getattr(settings, "dependency_retry_max_ms", 400)
    return RetryPolicy(
        attempts=int(attempts),
        base_seconds=int(base_ms) / 1000.0,
        max_seconds=int(max_ms) / 1000.0,
    )


_AI_CIRCUIT = CircuitBreaker("ai")
_STORAGE_CIRCUIT = CircuitBreaker("storage")


def ai_circuit() -> CircuitBreaker:
    return _AI_CIRCUIT


def storage_circuit() -> CircuitBreaker:
    return _STORAGE_CIRCUIT


def reset_circuits() -> None:
    _AI_CIRCUIT.reset()
    _STORAGE_CIRCUIT.reset()
