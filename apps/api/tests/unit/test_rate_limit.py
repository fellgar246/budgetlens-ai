from __future__ import annotations

from uuid import UUID

import pytest

from budgetlens.application.rate_limit import SlidingWindowLimiter, limiter
from budgetlens.domain.errors import RateLimitError


def test_sliding_window_rejects_burst() -> None:
    window = SlidingWindowLimiter()
    user = UUID(int=7)
    for _ in range(3):
        window.check(f"upload:{user}", limit=3, window_seconds=60)
    with pytest.raises(RateLimitError) as exc:
        window.check(f"upload:{user}", limit=3, window_seconds=60)
    assert exc.value.status_code == 429
    assert exc.value.retryable is True


def test_global_limiter_can_be_reset() -> None:
    limiter().reset()
    limiter().check("ai:reset", limit=1, window_seconds=60)
    with pytest.raises(RateLimitError):
        limiter().check("ai:reset", limit=1, window_seconds=60)
    limiter().reset()
    limiter().check("ai:reset", limit=1, window_seconds=60)
    limiter().reset()
