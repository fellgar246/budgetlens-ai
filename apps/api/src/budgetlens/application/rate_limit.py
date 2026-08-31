from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from uuid import UUID

from budgetlens.domain.errors import RateLimitError
from budgetlens.observability import metrics_registry


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._events[key]
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                metrics_registry().record_rate_limited()
                raise RateLimitError()
            bucket.append(now)

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


_LIMITER = SlidingWindowLimiter()


def limiter() -> SlidingWindowLimiter:
    return _LIMITER


def enforce_limit(action: str, user_id: UUID, *, limit: int, window_seconds: int = 60) -> None:
    _LIMITER.check(f"{action}:{user_id}", limit=limit, window_seconds=window_seconds)
