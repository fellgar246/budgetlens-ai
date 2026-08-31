from __future__ import annotations

from typing import Any
from uuid import UUID

from budgetlens.adapters.persistence.repositories import SqlAuditRepository
from budgetlens.domain.audit import AuditEvent, sanitized_metadata
from budgetlens.domain.identities import Clock, IdFactory


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
