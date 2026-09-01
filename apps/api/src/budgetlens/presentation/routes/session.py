from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, Request

from budgetlens.adapters.persistence.repositories import SqlMembershipRepository
from budgetlens.domain.enums import OrganizationStatus
from budgetlens.domain.errors import NotFoundError
from budgetlens.presentation.deps import (
    CurrentTenant,
    CurrentUser,
    DbSession,
    OptionalOrgId,
    OrgServiceDep,
    SettingsDep,
)
from budgetlens.presentation.schemas import (
    CreateOrganizationRequest,
    MeResponse,
    OrganizationListResponse,
    OrganizationResponse,
    PageInfo,
    PatchOrganizationRequest,
    me_response,
    organization_response,
)

router = APIRouter(tags=["session"])


@router.get("/me", response_model=MeResponse, operation_id="get_me")
def get_me(
    user: CurrentUser,
    settings: SettingsDep,
    organization_id: OptionalOrgId,
    session: DbSession,
) -> MeResponse:
    role = None
    if organization_id is not None:
        membership = SqlMembershipRepository(session, organization_id).get_for_user(user.id)
        if membership is not None and membership.is_active():
            role = membership.role
    return me_response(user, auth_mode=settings.auth_mode, role=role)


@router.get(
    "/organizations",
    response_model=OrganizationListResponse,
    operation_id="list_organizations",
)
def list_organizations(
    user: CurrentUser,
    service: OrgServiceDep,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
) -> OrganizationListResponse:
    page = service.list_for_user(user, cursor=cursor, limit=limit)
    return OrganizationListResponse(
        items=[
            organization_response(org, role=membership.role.value) for org, membership in page.items
        ],
        page=PageInfo(next_cursor=page.next_cursor, has_more=page.has_more),
    )


@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    status_code=201,
    operation_id="create_organization",
)
def create_organization(
    payload: CreateOrganizationRequest,
    request: Request,
    request_user: CurrentUser,
    service: OrgServiceDep,
) -> OrganizationResponse:
    organization = service.create(
        request_user,
        name=payload.name,
        slug=payload.slug,
        functional_currency=payload.functional_currency,
        fiscal_year_start_month=payload.fiscal_year_start_month,
        trace_id=str(getattr(request.state, "trace_id", "unknown")),
    )
    return organization_response(organization, role="admin")


@router.get(
    "/organizations/{organization_id}",
    response_model=OrganizationResponse,
    operation_id="get_organization",
)
def get_organization(
    organization_id: UUID,
    context: CurrentTenant,
    service: OrgServiceDep,
) -> OrganizationResponse:
    if organization_id != context.organization_id:
        raise NotFoundError()
    organization = service.get(context, organization_id)
    return organization_response(organization, role=context.role.value)


@router.patch(
    "/organizations/{organization_id}",
    response_model=OrganizationResponse,
    operation_id="patch_organization",
)
def patch_organization(
    organization_id: UUID,
    payload: PatchOrganizationRequest,
    context: CurrentTenant,
    service: OrgServiceDep,
) -> OrganizationResponse:
    if organization_id != context.organization_id:
        raise NotFoundError()
    organization = service.update(
        context,
        organization_id=organization_id,
        version=payload.version,
        name=payload.name,
        fiscal_year_start_month=payload.fiscal_year_start_month,
        status=OrganizationStatus(payload.status) if payload.status else None,
        conversation_retention_days=payload.conversation_retention_days,
    )
    return organization_response(organization, role=context.role.value)
