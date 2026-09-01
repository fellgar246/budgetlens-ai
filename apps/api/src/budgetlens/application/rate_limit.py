from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from uuid import UUID

from budgetlens.domain.errors import RateLimitError
from budgetlens.observability import metrics_registry


class ConcurrencyLimiter:
    def __init__(self) -> None:
        self._counts: dict[str, int] = {}
        self._lock = Lock()

    def acquire(self, key: str, *, limit: int) -> None:
        with self._lock:
            current = self._counts.get(key, 0)
            if current >= limit:
                metrics_registry().record_rate_limited()
                raise RateLimitError(
                    "Hay demasiadas consultas del copiloto en curso. Espera a que termine una."
                )
            self._counts[key] = current + 1

    def release(self, key: str) -> None:
        with self._lock:
            current = self._counts.get(key, 0)
            if current <= 1:
                self._counts.pop(key, None)
            else:
                self._counts[key] = current - 1

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        record_metric: bool = True,
    ) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                if record_metric:
                    metrics_registry().record_rate_limited()
                raise RateLimitError()
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()
        _CONCURRENCY.reset()


_LIMITER = SlidingWindowLimiter()
_CONCURRENCY = ConcurrencyLimiter()


def limiter() -> SlidingWindowLimiter:
    return _LIMITER


def concurrency_limiter() -> ConcurrencyLimiter:
    return _CONCURRENCY


def acquire_conversation_slot(user_id: UUID, *, organization_id: UUID, limit: int) -> None:
    _CONCURRENCY.acquire(f"ai-concurrent:{organization_id}:{user_id}", limit=limit)


def release_conversation_slot(user_id: UUID, *, organization_id: UUID) -> None:
    _CONCURRENCY.release(f"ai-concurrent:{organization_id}:{user_id}")


def enforce_limit(
    action: str,
    user_id: UUID,
    *,
    organization_id: UUID | None = None,
    limit: int,
    window_seconds: int = 60,
) -> None:
    key = f"{action}:{user_id}"
    if organization_id is not None:
        key = f"{action}:{organization_id}:{user_id}"
    _LIMITER.check(key, limit=limit, window_seconds=window_seconds)


def try_limit(
    action: str,
    user_id: UUID,
    *,
    organization_id: UUID | None = None,
    limit: int,
    window_seconds: int = 60,
) -> bool:
    key = f"{action}:{user_id}"
    if organization_id is not None:
        key = f"{action}:{organization_id}:{user_id}"
    try:
        _LIMITER.check(key, limit=limit, window_seconds=window_seconds, record_metric=False)
    except RateLimitError:
        return False
    return True
