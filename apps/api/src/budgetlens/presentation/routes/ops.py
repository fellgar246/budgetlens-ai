from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from budgetlens.domain.enums import Capability
from budgetlens.domain.permissions import require_capability
from budgetlens.observability import metrics_registry
from budgetlens.presentation.deps import CurrentUser, SettingsDep

router = APIRouter(tags=["ops"])


class OpsMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    requests: list[dict[str, Any]]
    active_requests: int
    db_pool: dict[str, int]
    db_rollbacks: int
    jobs: dict[str, Any]
    ai: dict[str, Any]
    rate_limited: int
    cost_estimate_configured: bool


@router.get("/ops/metrics", response_model=OpsMetricsResponse, operation_id="get_ops_metrics")
def get_ops_metrics(user: CurrentUser, settings: SettingsDep) -> OpsMetricsResponse:
    require_capability(
        role=None,
        capability=Capability.VIEW_TECHNICAL_METRICS,
        platform_role=user.platform_role,
    )
    snapshot = metrics_registry().snapshot(
        input_unit_cost_micros=settings.ai_input_unit_cost_micros,
        output_unit_cost_micros=settings.ai_output_unit_cost_micros,
    )
    return OpsMetricsResponse(
        requests=snapshot["requests"],
        active_requests=snapshot["active_requests"],
        db_pool=snapshot["db_pool"],
        db_rollbacks=snapshot["db_rollbacks"],
        jobs=snapshot["jobs"],
        ai=snapshot["ai"],
        rate_limited=snapshot["rate_limited"],
        cost_estimate_configured=bool(
            settings.ai_input_unit_cost_micros or settings.ai_output_unit_cost_micros
        ),
    )
