from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from budgetlens.application.analytics import parse_analytics_query
from budgetlens.application.scenarios import parse_rule_payload
from budgetlens.domain.enums import ScenarioType
from budgetlens.presentation.deps import CurrentTenant, ScenarioServiceDep
from budgetlens.presentation.schemas import PageInfo
from budgetlens.presentation.schemas_ops import (
    CreateScenarioRequest,
    PatchScenarioRequest,
    PreviewScenarioRequest,
    ScenarioListResponse,
    ScenarioResponse,
    scenario_response,
)

router = APIRouter(tags=["scenarios"])


@router.get("/scenarios", response_model=ScenarioListResponse, operation_id="list_scenarios")
def list_scenarios(
    context: CurrentTenant,
    service: ScenarioServiceDep,
    cursor: str | None = None,
    limit: int | None = Query(default=None, ge=1, le=100),
) -> ScenarioListResponse:
    page = service.list(context, cursor=cursor, limit=limit)
    return ScenarioListResponse(
        items=[scenario_response(item) for item in page.items],
        page=PageInfo(next_cursor=page.next_cursor, has_more=page.has_more),
    )


@router.post(
    "/scenarios", response_model=ScenarioResponse, status_code=201, operation_id="create_scenario"
)
def create_scenario(
    payload: CreateScenarioRequest,
    context: CurrentTenant,
    service: ScenarioServiceDep,
) -> ScenarioResponse:
    return scenario_response(
        service.create(
            context,
            name=payload.name,
            baseline_type=ScenarioType(payload.baseline_type),
            budget_version_id=payload.budget_version_id,
            fiscal_year=payload.fiscal_year,
            rules=[parse_rule_payload(item.model_dump()) for item in payload.rules],
        )
    )


@router.get(
    "/scenarios/{scenario_id}", response_model=ScenarioResponse, operation_id="get_scenario"
)
def get_scenario(
    scenario_id: UUID, context: CurrentTenant, service: ScenarioServiceDep
) -> ScenarioResponse:
    return scenario_response(service.get(context, scenario_id))


@router.patch(
    "/scenarios/{scenario_id}", response_model=ScenarioResponse, operation_id="patch_scenario"
)
def patch_scenario(
    scenario_id: UUID,
    payload: PatchScenarioRequest,
    context: CurrentTenant,
    service: ScenarioServiceDep,
) -> ScenarioResponse:
    return scenario_response(
        service.update(
            context,
            scenario_id=scenario_id,
            name=payload.name,
            rules=[parse_rule_payload(item.model_dump()) for item in payload.rules]
            if payload.rules is not None
            else None,
        )
    )


@router.post("/scenarios/preview", operation_id="preview_scenario")
def preview_scenario(
    payload: PreviewScenarioRequest,
    context: CurrentTenant,
    service: ScenarioServiceDep,
) -> dict[str, object]:
    query = parse_analytics_query(
        fiscal_year=payload.fiscal_year,
        period_from=payload.period_from,
        period_to=payload.period_to,
        budget_version_id=payload.budget_version_id,
        account_ids=payload.account_ids,
        department_ids=payload.department_ids,
        cost_center_ids=payload.cost_center_ids,
    )
    return service.preview(
        context,
        query=query,
        baseline_type=ScenarioType(payload.baseline_type),
        rules=[parse_rule_payload(item.model_dump()) for item in payload.rules],
    )


@router.post(
    "/scenarios/{scenario_id}/archive",
    response_model=ScenarioResponse,
    operation_id="archive_scenario",
)
def archive_scenario(
    scenario_id: UUID, context: CurrentTenant, service: ScenarioServiceDep
) -> ScenarioResponse:
    return scenario_response(service.archive(context, scenario_id=scenario_id))
