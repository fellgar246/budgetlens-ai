from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from budgetlens.presentation.deps import BudgetVersionServiceDep, CurrentTenant
from budgetlens.presentation.headers import RequiredIdempotencyKey
from budgetlens.presentation.schemas import (
    BudgetVersionListResponse,
    BudgetVersionResponse,
    CreateBudgetVersionRequest,
    PageInfo,
    PatchBudgetVersionRequest,
    budget_version_response,
)

router = APIRouter(tags=["budget-versions"])


@router.get(
    "/budget-versions",
    response_model=BudgetVersionListResponse,
    operation_id="list_budget_versions",
)
def list_budget_versions(
    context: CurrentTenant,
    service: BudgetVersionServiceDep,
    fiscal_year: int | None = None,
    include_archived: bool = False,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
) -> BudgetVersionListResponse:
    page = service.list(
        context,
        cursor=cursor,
        limit=limit,
        fiscal_year=fiscal_year,
        include_archived=include_archived,
    )
    return BudgetVersionListResponse(
        items=[budget_version_response(item) for item in page.items],
        page=PageInfo(next_cursor=page.next_cursor, has_more=page.has_more),
    )


@router.post(
    "/budget-versions",
    response_model=BudgetVersionResponse,
    status_code=201,
    operation_id="create_budget_version",
)
def create_budget_version(
    payload: CreateBudgetVersionRequest,
    context: CurrentTenant,
    service: BudgetVersionServiceDep,
) -> BudgetVersionResponse:
    return budget_version_response(
        service.create(context, name=payload.name, fiscal_year=payload.fiscal_year)
    )


@router.get(
    "/budget-versions/{version_id}",
    response_model=BudgetVersionResponse,
    operation_id="get_budget_version",
)
def get_budget_version(
    version_id: UUID,
    context: CurrentTenant,
    service: BudgetVersionServiceDep,
) -> BudgetVersionResponse:
    return budget_version_response(service.get(context, version_id))


@router.patch(
    "/budget-versions/{version_id}",
    response_model=BudgetVersionResponse,
    operation_id="patch_budget_version",
)
def patch_budget_version(
    version_id: UUID,
    payload: PatchBudgetVersionRequest,
    context: CurrentTenant,
    service: BudgetVersionServiceDep,
) -> BudgetVersionResponse:
    return budget_version_response(
        service.update(
            context,
            version_id=version_id,
            expected_version=payload.version,
            name=payload.name,
        )
    )


@router.post(
    "/budget-versions/{version_id}/publish",
    response_model=BudgetVersionResponse,
    operation_id="publish_budget_version",
)
def publish_budget_version(
    version_id: UUID,
    context: CurrentTenant,
    service: BudgetVersionServiceDep,
    idempotency_key: RequiredIdempotencyKey,
) -> BudgetVersionResponse:
    return budget_version_response(
        service.publish(context, version_id=version_id, idempotency_key=idempotency_key)
    )


@router.post(
    "/budget-versions/{version_id}/activate",
    response_model=BudgetVersionResponse,
    operation_id="activate_budget_version",
)
def activate_budget_version(
    version_id: UUID,
    context: CurrentTenant,
    service: BudgetVersionServiceDep,
    idempotency_key: RequiredIdempotencyKey,
) -> BudgetVersionResponse:
    return budget_version_response(
        service.activate(context, version_id=version_id, idempotency_key=idempotency_key)
    )


@router.post(
    "/budget-versions/{version_id}/archive",
    response_model=BudgetVersionResponse,
    operation_id="archive_budget_version",
)
def archive_budget_version(
    version_id: UUID,
    context: CurrentTenant,
    service: BudgetVersionServiceDep,
    idempotency_key: RequiredIdempotencyKey,
) -> BudgetVersionResponse:
    return budget_version_response(
        service.archive(context, version_id=version_id, idempotency_key=idempotency_key)
    )
