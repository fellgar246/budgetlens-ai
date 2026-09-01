from __future__ import annotations

from typing import Any
from uuid import UUID, uuid5

from budgetlens.adapters.db import get_session_factory
from budgetlens.adapters.persistence.repositories import SqlAuditRepository
from budgetlens.application.rate_limit import enforce_limit, try_limit
from budgetlens.config import get_settings
from budgetlens.domain.audit import (
    ACTOR_SYSTEM,
    ACTOR_USER,
    AUTH_LOGIN_FAILED,
    AUTH_LOGIN_SUCCEEDED,
    SECURITY_ACCESS_DENIED,
    SYSTEM_AUTH,
    AuditEvent,
    sanitized_metadata,
)
from budgetlens.domain.errors import RateLimitError
from budgetlens.domain.identities import Clock, IdFactory, SystemClock, Uuid4Factory

_AUTH_NAMESPACE = UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def record_audit(
    audits: SqlAuditRepository,
    *,
    clock: Clock,
    ids: IdFactory,
    organization_id: UUID | None,
    action: str,
    resource_type: str,
    resource_id: UUID,
    trace_id: str,
    actor_id: UUID | None = None,
    actor_type: str = ACTOR_USER,
    actor_ref: str | None = None,
    metadata: dict[str, Any] | None = None,
    outcome: str = "success",
) -> None:
    if actor_type == ACTOR_USER and actor_id is None:
        raise ValueError("user audit events require actor_id")
    identity = actor_ref or (str(actor_id) if actor_id is not None else SYSTEM_AUTH)
    payload = sanitized_metadata(metadata or {})
    try:
        version = get_settings().app_version
    except Exception:
        version = None
    if version and "app_version" not in payload:
        payload["app_version"] = version
    audits.add(
        AuditEvent(
            id=ids.new_id(),
            organization_id=organization_id,
            actor_type=actor_type,
            actor_id=actor_id,
            actor_ref=identity,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            metadata=payload,
            trace_id=trace_id,
            created_at=clock.now(),
        )
    )


def _commit_standalone(
    *,
    organization_id: UUID | None,
    actor_id: UUID | None,
    actor_type: str,
    actor_ref: str,
    action: str,
    resource_type: str,
    resource_id: UUID,
    trace_id: str,
    metadata: dict[str, Any] | None,
    outcome: str,
) -> None:
    session = get_session_factory()()
    try:
        record_audit(
            SqlAuditRepository(session),
            clock=SystemClock(),
            ids=Uuid4Factory(),
            organization_id=organization_id,
            actor_id=actor_id,
            actor_type=actor_type,
            actor_ref=actor_ref,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            trace_id=trace_id,
            metadata=metadata,
            outcome=outcome,
        )
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def record_access_denied(
    *,
    actor_id: UUID | None,
    organization_id: UUID | None,
    resource_id: UUID,
    trace_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if actor_id is None:
        return
    try:
        enforce_limit("access_denied", actor_id, limit=5, window_seconds=60)
    except RateLimitError:
        return
    _commit_standalone(
        organization_id=organization_id,
        actor_id=actor_id,
        actor_type=ACTOR_USER,
        actor_ref=str(actor_id),
        action=SECURITY_ACCESS_DENIED,
        resource_type="security",
        resource_id=resource_id,
        trace_id=trace_id,
        metadata=metadata,
        outcome="denied",
    )


def record_login_succeeded(
    *,
    actor_id: UUID,
    organization_id: UUID | None,
    trace_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    if not try_limit("login_succeeded", actor_id, limit=1, window_seconds=900):
        return
    _commit_standalone(
        organization_id=organization_id,
        actor_id=actor_id,
        actor_type=ACTOR_USER,
        actor_ref=str(actor_id),
        action=AUTH_LOGIN_SUCCEEDED,
        resource_type="auth",
        resource_id=actor_id,
        trace_id=trace_id,
        metadata=metadata,
        outcome="success",
    )


def record_login_failed(
    *,
    organization_id: UUID | None,
    trace_id: str,
    metadata: dict[str, Any] | None = None,
) -> None:
    try:
        enforce_limit("login_failed", UUID(int=0), limit=8, window_seconds=60)
    except RateLimitError:
        return
    _commit_standalone(
        organization_id=organization_id,
        actor_id=None,
        actor_type=ACTOR_SYSTEM,
        actor_ref=SYSTEM_AUTH,
        action=AUTH_LOGIN_FAILED,
        resource_type="auth",
        resource_id=uuid5(_AUTH_NAMESPACE, "login_failed"),
        trace_id=trace_id,
        metadata=metadata,
        outcome="failed",
    )
