from __future__ import annotations

from uuid import UUID

import pytest

from budgetlens.application.rate_limit import (
    acquire_conversation_slot,
    concurrency_limiter,
    limiter,
    release_conversation_slot,
)
from budgetlens.domain.errors import RateLimitError


def test_concurrent_conversation_slots_are_limited() -> None:
    limiter().reset()
    user = UUID(int=21)
    org = UUID(int=22)
    acquire_conversation_slot(user, organization_id=org, limit=2)
    acquire_conversation_slot(user, organization_id=org, limit=2)
    with pytest.raises(RateLimitError) as exc:
        acquire_conversation_slot(user, organization_id=org, limit=2)
    assert exc.value.retryable is True
    release_conversation_slot(user, organization_id=org)
    acquire_conversation_slot(user, organization_id=org, limit=2)
    release_conversation_slot(user, organization_id=org)
    release_conversation_slot(user, organization_id=org)
    concurrency_limiter().reset()
