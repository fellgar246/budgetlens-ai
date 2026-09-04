from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import Response

from budgetlens.application.analytics import parse_analytics_query
from budgetlens.domain.enums import AnalyticsGroupBy, AnalyticsSort, SortDirection
from budgetlens.presentation.deps import AnalyticsServiceDep, CurrentTenant
from budgetlens.presentation.schemas import PageInfo
from budgetlens.presentation.schemas_ops import (
    BreakdownListResponse,
    ComparePeriodsResponse,
    CreateExportRequest,
    ExportJobResponse,
    VarianceSummaryResponse,
    breakdown_item_response,
    export_job_response,
    summary_response,
)

router = APIRouter(tags=["analytics"])
RepeatUuid = Annotated[list[UUID] | None, Query()]


def _query(
    fiscal_year: int,
    period_from: date,
    period_to: date,
    budget_version_id: UUID,
    account_id: list[UUID] | None,
    department_id: list[UUID] | None,
    cost_center_id: list[UUID] | None,
):
    return parse_analytics_query(
        fiscal_year=fiscal_year,
        period_from=period_from,
        period_to=period_to,
        budget_version_id=budget_version_id,
        account_ids=account_id,
        department_ids=department_id,
        cost_center_ids=cost_center_id,
    )


@router.get(
    "/analytics/variance-summary",
    response_model=VarianceSummaryResponse,
    operation_id="get_variance_summary",
)
def get_variance_summary(
    context: CurrentTenant,
    service: AnalyticsServiceDep,
    fiscal_year: int,
    period_from: date,
    period_to: date,
    budget_version_id: UUID,
    account_id: RepeatUuid = None,
    department_id: RepeatUuid = None,
    cost_center_id: RepeatUuid = None,
) -> VarianceSummaryResponse:
    return summary_response(
        service.summary(
            context,
            _query(
                fiscal_year,
                period_from,
                period_to,
                budget_version_id,
                account_id,
                department_id,
                cost_center_id,
            ),
        )
    )


@router.get(
    "/analytics/variance-breakdown",
    response_model=BreakdownListResponse,
    operation_id="get_variance_breakdown",
)
def get_variance_breakdown(
    context: CurrentTenant,
    service: AnalyticsServiceDep,
    fiscal_year: int,
    period_from: date,
    period_to: date,
    budget_version_id: UUID,
    group_by: AnalyticsGroupBy = AnalyticsGroupBy.DEPARTMENT,
    sort: AnalyticsSort = AnalyticsSort.ABSOLUTE_VARIANCE,
    direction: SortDirection = SortDirection.DESC,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
    account_id: RepeatUuid = None,
    department_id: RepeatUuid = None,
    cost_center_id: RepeatUuid = None,
) -> BreakdownListResponse:
    page = service.breakdown(
        context,
        _query(
            fiscal_year,
            period_from,
            period_to,
            budget_version_id,
            account_id,
            department_id,
            cost_center_id,
        ),
        group_by=group_by,
        sort=sort,
        direction=direction,
        cursor=cursor,
        limit=limit,
    )
    return BreakdownListResponse(
        items=[breakdown_item_response(item) for item in page.items],
        page=PageInfo(next_cursor=page.next_cursor, has_more=page.has_more),
    )


@router.get(
    "/analytics/top-unfavorable",
    response_model=BreakdownListResponse,
    operation_id="get_top_unfavorable",
)
def get_top_unfavorable(
    context: CurrentTenant,
    service: AnalyticsServiceDep,
    fiscal_year: int,
    period_from: date,
    period_to: date,
    budget_version_id: UUID,
    group_by: AnalyticsGroupBy = AnalyticsGroupBy.ACCOUNT,
    limit: int = Query(default=10, ge=1, le=20),
    account_id: RepeatUuid = None,
    department_id: RepeatUuid = None,
    cost_center_id: RepeatUuid = None,
) -> BreakdownListResponse:
    items = service.top_unfavorable(
        context,
        _query(
            fiscal_year,
            period_from,
            period_to,
            budget_version_id,
            account_id,
            department_id,
            cost_center_id,
        ),
        group_by=group_by,
        limit=limit,
    )
    return BreakdownListResponse(
        items=[breakdown_item_response(item) for item in items],
        page=PageInfo(next_cursor=None, has_more=False),
    )


@router.get(
    "/analytics/compare-periods",
    response_model=ComparePeriodsResponse,
    operation_id="compare_periods",
)
def compare_periods(
    context: CurrentTenant,
    service: AnalyticsServiceDep,
    fiscal_year: int,
    period_from: date,
    period_to: date,
    budget_version_id: UUID,
    compare_from: date,
    compare_to: date,
    account_id: RepeatUuid = None,
    department_id: RepeatUuid = None,
    cost_center_id: RepeatUuid = None,
) -> ComparePeriodsResponse:
    compared = service.compare_periods(
        context,
        _query(
            fiscal_year,
            period_from,
            period_to,
            budget_version_id,
            account_id,
            department_id,
            cost_center_id,
        ),
        compare_from=compare_from,
        compare_to=compare_to,
    )
    return ComparePeriodsResponse(
        baseline=summary_response(compared["baseline"]),
        comparison=summary_response(compared["comparison"]),
    )


@router.post("/exports", response_model=ExportJobResponse, operation_id="create_export")
def create_export(
    payload: CreateExportRequest,
    context: CurrentTenant,
    service: AnalyticsServiceDep,
) -> ExportJobResponse:
    return export_job_response(
        service.export_breakdown(
            context, payload.filters.to_query(), group_by=AnalyticsGroupBy(payload.group_by)
        )
    )


@router.get("/exports/{export_id}/content", operation_id="download_export")
def download_export(
    export_id: UUID, context: CurrentTenant, service: AnalyticsServiceDep
) -> Response:
    job, content = service.get_export(context, export_id)
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{job.filename}"'},
    )
