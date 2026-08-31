from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from budgetlens.domain.enums import AccountType, DimensionStatus
from budgetlens.presentation.deps import CurrentTenant, DimensionServiceDep
from budgetlens.presentation.schemas import (
    AccountListResponse,
    AccountResponse,
    CostCenterListResponse,
    CostCenterResponse,
    CreateAccountRequest,
    CreateCostCenterRequest,
    CreateDepartmentRequest,
    DepartmentListResponse,
    DepartmentResponse,
    PageInfo,
    PatchAccountRequest,
    PatchCostCenterRequest,
    PatchDepartmentRequest,
    account_response,
    cost_center_response,
    department_response,
)

router = APIRouter(tags=["dimensions"])


def _page(next_cursor: str | None, has_more: bool) -> PageInfo:
    return PageInfo(next_cursor=next_cursor, has_more=has_more)


@router.get("/accounts", response_model=AccountListResponse, operation_id="list_accounts")
def list_accounts(
    context: CurrentTenant,
    service: DimensionServiceDep,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
) -> AccountListResponse:
    page = service.list_accounts(context, cursor=cursor, limit=limit, status=status, search=search)
    return AccountListResponse(
        items=[account_response(item) for item in page.items],
        page=_page(page.next_cursor, page.has_more),
    )


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=201,
    operation_id="create_account",
)
def create_account(
    payload: CreateAccountRequest,
    context: CurrentTenant,
    service: DimensionServiceDep,
) -> AccountResponse:
    return account_response(
        service.create_account(
            context,
            code=payload.code,
            name=payload.name,
            account_type=AccountType(payload.account_type),
            parent_id=payload.parent_id,
        )
    )


@router.get("/accounts/{account_id}", response_model=AccountResponse, operation_id="get_account")
def get_account(
    account_id: UUID,
    context: CurrentTenant,
    service: DimensionServiceDep,
) -> AccountResponse:
    return account_response(service.get_account(context, account_id))


@router.patch(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    operation_id="patch_account",
)
def patch_account(
    account_id: UUID,
    payload: PatchAccountRequest,
    context: CurrentTenant,
    service: DimensionServiceDep,
) -> AccountResponse:
    return account_response(
        service.update_account(
            context,
            account_id=account_id,
            name=payload.name,
            account_type=AccountType(payload.account_type) if payload.account_type else None,
            parent_id=payload.parent_id,
            clear_parent=payload.clear_parent,
            status=DimensionStatus(payload.status) if payload.status else None,
        )
    )


@router.get("/departments", response_model=DepartmentListResponse, operation_id="list_departments")
def list_departments(
    context: CurrentTenant,
    service: DimensionServiceDep,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
) -> DepartmentListResponse:
    page = service.list_departments(
        context, cursor=cursor, limit=limit, status=status, search=search
    )
    return DepartmentListResponse(
        items=[department_response(item) for item in page.items],
        page=_page(page.next_cursor, page.has_more),
    )


@router.post(
    "/departments",
    response_model=DepartmentResponse,
    status_code=201,
    operation_id="create_department",
)
def create_department(
    payload: CreateDepartmentRequest,
    context: CurrentTenant,
    service: DimensionServiceDep,
) -> DepartmentResponse:
    return department_response(
        service.create_department(context, code=payload.code, name=payload.name)
    )


@router.get(
    "/departments/{department_id}",
    response_model=DepartmentResponse,
    operation_id="get_department",
)
def get_department(
    department_id: UUID,
    context: CurrentTenant,
    service: DimensionServiceDep,
) -> DepartmentResponse:
    return department_response(service.get_department(context, department_id))


@router.patch(
    "/departments/{department_id}",
    response_model=DepartmentResponse,
    operation_id="patch_department",
)
def patch_department(
    department_id: UUID,
    payload: PatchDepartmentRequest,
    context: CurrentTenant,
    service: DimensionServiceDep,
) -> DepartmentResponse:
    return department_response(
        service.update_department(
            context,
            department_id=department_id,
            name=payload.name,
            status=DimensionStatus(payload.status) if payload.status else None,
        )
    )


@router.get(
    "/cost-centers",
    response_model=CostCenterListResponse,
    operation_id="list_cost_centers",
)
def list_cost_centers(
    context: CurrentTenant,
    service: DimensionServiceDep,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
    status: str | None = None,
    search: str | None = None,
) -> CostCenterListResponse:
    page = service.list_cost_centers(
        context, cursor=cursor, limit=limit, status=status, search=search
    )
    return CostCenterListResponse(
        items=[cost_center_response(item) for item in page.items],
        page=_page(page.next_cursor, page.has_more),
    )


@router.post(
    "/cost-centers",
    response_model=CostCenterResponse,
    status_code=201,
    operation_id="create_cost_center",
)
def create_cost_center(
    payload: CreateCostCenterRequest,
    context: CurrentTenant,
    service: DimensionServiceDep,
) -> CostCenterResponse:
    return cost_center_response(
        service.create_cost_center(context, code=payload.code, name=payload.name)
    )


@router.get(
    "/cost-centers/{cost_center_id}",
    response_model=CostCenterResponse,
    operation_id="get_cost_center",
)
def get_cost_center(
    cost_center_id: UUID,
    context: CurrentTenant,
    service: DimensionServiceDep,
) -> CostCenterResponse:
    return cost_center_response(service.get_cost_center(context, cost_center_id))


@router.patch(
    "/cost-centers/{cost_center_id}",
    response_model=CostCenterResponse,
    operation_id="patch_cost_center",
)
def patch_cost_center(
    cost_center_id: UUID,
    payload: PatchCostCenterRequest,
    context: CurrentTenant,
    service: DimensionServiceDep,
) -> CostCenterResponse:
    return cost_center_response(
        service.update_cost_center(
            context,
            cost_center_id=cost_center_id,
            name=payload.name,
            status=DimensionStatus(payload.status) if payload.status else None,
            code=None,
        )
    )
