from __future__ import annotations

from typing import Any
from uuid import UUID

from budgetlens.adapters.db import get_session_factory
from budgetlens.adapters.persistence.repositories import SqlAuditRepository
from budgetlens.application.rate_limit import enforce_limit
from budgetlens.domain.audit import AuditEvent, sanitized_metadata
from budgetlens.domain.errors import RateLimitError
from budgetlens.domain.identities import Clock, IdFactory, SystemClock, Uuid4Factory


def record_audit(
    audits: SqlAuditRepository,
    *,
    clock: Clock,
    ids: IdFactory,
    organization_id: UUID | None,
    actor_id: UUID,
    action: str,
    resource_type: str,
    resource_id: UUID,
    trace_id: str,
    metadata: dict[str, Any] | None = None,
    outcome: str = "success",
) -> None:
    audits.add(
        AuditEvent(
            id=ids.new_id(),
            organization_id=organization_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            outcome=outcome,
            metadata=sanitized_metadata(metadata or {}),
            trace_id=trace_id,
            created_at=clock.now(),
        )
    )


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
    session = get_session_factory()()
    try:
        record_audit(
            SqlAuditRepository(session),
            clock=SystemClock(),
            ids=Uuid4Factory(),
            organization_id=organization_id,
            actor_id=actor_id,
            action="security.access_denied",
            resource_type="security",
            resource_id=resource_id,
            trace_id=trace_id,
            metadata=metadata,
            outcome="denied",
        )
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()
