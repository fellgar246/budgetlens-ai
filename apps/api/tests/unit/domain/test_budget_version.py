from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from budgetlens.domain.budget_version import BudgetVersion
from budgetlens.domain.enums import BudgetVersionStatus
from budgetlens.domain.errors import ConflictError
from budgetlens.domain.identities import FrozenClock, SequentialIdFactory


def _version(
    *, status: BudgetVersionStatus = BudgetVersionStatus.DRAFT, active: bool = False
) -> BudgetVersion:
    clock = FrozenClock(datetime(2026, 1, 15, tzinfo=UTC))
    ids = SequentialIdFactory()
    return BudgetVersion(
        id=ids.new_id(),
        organization_id=ids.new_id(),
        name="Plan inicial",
        fiscal_year=2026,
        status=status,
        is_active=active,
        published_at=clock.now() if status is not BudgetVersionStatus.DRAFT else None,
        published_by=ids.new_id() if status is not BudgetVersionStatus.DRAFT else None,
        created_at=clock.now(),
        version=1,
    )


def test_publish_makes_version_immutable() -> None:
    clock = FrozenClock(datetime(2026, 2, 1, tzinfo=UTC))
    actor = UUID(int=9)
    published = _version().publish(now=clock.now(), actor_id=actor)
    assert published.status is BudgetVersionStatus.PUBLISHED
    assert published.published_at == clock.now()
    assert published.published_by == actor
    with pytest.raises(ConflictError) as exc:
        published.with_draft_metadata(expected_version=published.version, name="Otro nombre")
    assert exc.value.code == "VERSION_NOT_DRAFT"


def test_republish_is_idempotent() -> None:
    clock = FrozenClock(datetime(2026, 2, 1, tzinfo=UTC))
    actor = UUID(int=9)
    first = _version().publish(now=clock.now(), actor_id=actor)
    second = first.publish(now=clock.now(), actor_id=actor)
    assert first == second


def test_only_published_can_activate() -> None:
    with pytest.raises(ConflictError) as exc:
        _version().activate()
    assert exc.value.code == "VERSION_NOT_PUBLISHED"
    active = _version(status=BudgetVersionStatus.PUBLISHED).activate()
    assert active.is_active is True


def test_archive_keeps_trace_and_clears_active() -> None:
    clock = FrozenClock(datetime(2026, 3, 1, tzinfo=UTC))
    archived = _version(status=BudgetVersionStatus.PUBLISHED, active=True).archive(now=clock.now())
    assert archived.status is BudgetVersionStatus.ARCHIVED
    assert archived.is_active is False
    assert archived.published_at is not None
    assert archived.appears_in_default_list() is False


def test_published_version_does_not_accept_entries() -> None:
    published = _version(status=BudgetVersionStatus.PUBLISHED)
    with pytest.raises(ConflictError) as exc:
        published.assert_accepts_entries()
    assert exc.value.code == "VERSION_NOT_DRAFT"
    _version().assert_accepts_entries()
