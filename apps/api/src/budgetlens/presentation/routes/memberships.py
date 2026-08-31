from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from budgetlens.domain.enums import MembershipStatus, Role
from budgetlens.presentation.deps import CurrentTenant, MembershipServiceDep
from budgetlens.presentation.schemas import (
    CreateMembershipRequest,
    MembershipListResponse,
    MembershipResponse,
    PageInfo,
    PatchMembershipRequest,
    membership_response,
)

router = APIRouter(tags=["memberships"])


@router.get("/memberships", response_model=MembershipListResponse, operation_id="list_memberships")
def list_memberships(
    context: CurrentTenant,
    service: MembershipServiceDep,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
) -> MembershipListResponse:
    page = service.list(context, cursor=cursor, limit=limit)
    return MembershipListResponse(
        items=[membership_response(item) for item in page.items],
        page=PageInfo(next_cursor=page.next_cursor, has_more=page.has_more),
    )


@router.post(
    "/memberships",
    response_model=MembershipResponse,
    status_code=201,
    operation_id="create_membership",
)
def create_membership(
    payload: CreateMembershipRequest,
    context: CurrentTenant,
    service: MembershipServiceDep,
) -> MembershipResponse:
    return membership_response(
        service.create(context, user_id=payload.user_id, role=Role(payload.role))
    )


@router.patch(
    "/memberships/{membership_id}",
    response_model=MembershipResponse,
    operation_id="patch_membership",
)
def patch_membership(
    membership_id: UUID,
    payload: PatchMembershipRequest,
    context: CurrentTenant,
    service: MembershipServiceDep,
) -> MembershipResponse:
    return membership_response(
        service.update(
            context,
            membership_id=membership_id,
            role=Role(payload.role) if payload.role else None,
            status=MembershipStatus(payload.status) if payload.status else None,
        )
    )
