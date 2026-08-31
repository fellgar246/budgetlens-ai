from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query

from budgetlens.adapters.persistence.repositories import SqlAuditRepository
from budgetlens.application.pagination import clamp_limit
from budgetlens.domain.enums import Permission
from budgetlens.domain.permissions import require_permission
from budgetlens.presentation.deps import CurrentTenant, DbSession
from budgetlens.presentation.schemas import PageInfo
from budgetlens.presentation.schemas_ops import AuditEventListResponse, audit_event_response

router = APIRouter(tags=["audit"])


@router.get(
    "/audit-events", response_model=AuditEventListResponse, operation_id="list_audit_events"
)
def list_audit_events(
    context: CurrentTenant,
    session: DbSession,
    action: str | None = None,
    actor_id: UUID | None = None,
    resource_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
) -> AuditEventListResponse:
    require_permission(context.role, Permission.MANAGE_ORGANIZATION)
    page = SqlAuditRepository(session).list_page(
        organization_id=context.organization_id,
        cursor=cursor,
        limit=clamp_limit(limit),
        action=action,
        actor_id=actor_id,
        resource_type=resource_type,
        date_from=date_from,
        date_to=date_to,
    )
    return AuditEventListResponse(
        items=[audit_event_response(item) for item in page.items],
        page=PageInfo(next_cursor=page.next_cursor, has_more=page.has_more),
    )
