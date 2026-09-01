from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from budgetlens.domain.conversation import (
    CONVERSATION_CONTENT_FULL_SYNTHETIC,
    CONVERSATION_CONTENT_REDACTED,
    REDACTED_MESSAGE_CONTENT,
    Conversation,
    persistable_message_content,
)
from budgetlens.domain.enums import MessageRole, OrganizationStatus, UserStatus
from budgetlens.domain.errors import UnauthenticatedError, ValidationError
from budgetlens.domain.money import Currency
from budgetlens.domain.organization import Organization, User, require_same_organization


def _now() -> datetime:
    return datetime(2026, 1, 15, tzinfo=UTC)


def test_disabled_user_cannot_start_a_session() -> None:
    user = User(
        id=UUID(int=1),
        email="ana@example.com",
        display_name="Ana",
        status=UserStatus.DISABLED,
        external_subject=None,
        created_at=_now(),
        updated_at=_now(),
    )
    with pytest.raises(UnauthenticatedError):
        user.assert_active()


def test_organization_update_keeps_created_at() -> None:
    created = _now()
    organization = Organization(
        id=UUID(int=2),
        name="Alpha",
        slug="alpha",
        functional_currency=Currency("MXN"),
        fiscal_year_start_month=1,
        status=OrganizationStatus.ACTIVE,
        created_at=created,
        updated_at=created,
        version=1,
    )
    later = datetime(2026, 2, 1, tzinfo=UTC)
    updated = organization.with_updates(expected_version=1, now=later, name="Alpha Ops")
    assert updated.created_at == created
    assert updated.updated_at == later
    assert updated.version == 2
    with pytest.raises(ValidationError):
        organization.with_updates(
            expected_version=1,
            now=later,
            conversation_retention_days=400,
        )
    retained = organization.with_updates(
        expected_version=1,
        now=later,
        conversation_retention_days=30,
    )
    assert retained.conversation_retention_days == 30


def test_same_organization_is_required() -> None:
    require_same_organization(UUID(int=1), UUID(int=1))
    with pytest.raises(ValidationError) as exc:
        require_same_organization(UUID(int=1), UUID(int=2))
    assert exc.value.code == "TENANT_MISMATCH"


def test_conversation_stays_in_its_organization() -> None:
    conversation = Conversation(
        id=UUID(int=9),
        organization_id=UUID(int=1),
        user_id=UUID(int=2),
        title="Consulta",
        context_filters={},
        created_at=_now(),
        updated_at=_now(),
        deleted_at=None,
    )
    conversation.assert_same_organization(UUID(int=1))
    with pytest.raises(ValidationError) as exc:
        conversation.assert_same_organization(UUID(int=3))
    assert exc.value.code == "CONVERSATION_ORG_MISMATCH"
    deleted = conversation.soft_delete(now=datetime(2026, 2, 1, tzinfo=UTC))
    assert deleted.organization_id == conversation.organization_id
    message = conversation.message(
        message_id=UUID(int=11),
        role=MessageRole.USER,
        content="¿Cuál fue el gasto?",
        created_at=_now(),
    )
    assert message.organization_id == conversation.organization_id
    assert message.conversation_id == conversation.id


def test_conversation_persistence_redacts_outside_synthetic_mode() -> None:
    question = "¿Cuál fue el gasto?"
    assert (
        persistable_message_content(question, mode=CONVERSATION_CONTENT_FULL_SYNTHETIC) == question
    )
    assert (
        persistable_message_content(question, mode=CONVERSATION_CONTENT_REDACTED)
        == REDACTED_MESSAGE_CONTENT
    )
    with pytest.raises(ValidationError) as exc:
        persistable_message_content(question, mode="encrypted")
    assert exc.value.code == "INVALID_CONTENT_MODE"
