from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from budgetlens.application.ai import CopilotAnswer
from budgetlens.application.analytics import BreakdownItem, VarianceMetrics, VarianceSummary
from budgetlens.domain.audit import AuditEvent, sanitized_metadata
from budgetlens.domain.conversation import Conversation
from budgetlens.domain.enums import ScenarioType
from budgetlens.domain.exporting import ExportJob
from budgetlens.domain.importing import ImportIssue, ImportJob
from budgetlens.domain.scenario import Scenario
from budgetlens.presentation.schemas import PageInfo


class CreateImportRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "import_type": "actual",
                "budget_version_id": None,
                "original_filename": "actuals-2026.xlsx",
                "size_bytes": 123456,
                "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "template_version": "1.0",
            }
        },
    )
    import_type: Literal["budget", "actual"]
    budget_version_id: UUID | None = None
    original_filename: str
    size_bytes: int = Field(ge=1)
    sha256: str
    template_version: str = "1.0"


class ValidateImportRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "mapping": {
                    "period": "Month",
                    "account_code": "Account",
                    "department_code": "Department",
                    "cost_center_code": "Cost Center",
                    "amount": "Actual",
                    "currency": "Currency",
                },
                "create_missing_dimensions": False,
            }
        },
    )
    mapping: dict[str, str]
    create_missing_dimensions: bool = False
    amount_locale: Literal["en", "es"] = "en"


class ImportUploadInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: str
    method: str
    url: str


class ImportJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    organization_id: UUID
    import_type: str
    budget_version_id: UUID | None
    status: str
    original_filename: str
    sha256: str
    size_bytes: int
    template_version: str
    mapping: dict[str, Any]
    row_count: int
    valid_count: int
    error_count: int
    warning_count: int
    period_min: date | None
    period_max: date | None
    valid_amount_total: str
    sheet_name: str | None
    failure_code: str | None
    created_at: datetime
    upload: ImportUploadInfo | None = None


class ImportJobListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ImportJobResponse]
    page: PageInfo


class ImportPreviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job: ImportJobResponse
    headers: list[str]
    proposed_mapping: dict[str, str]
    items: list[dict[str, str]]
    new_accounts: int
    new_departments: int
    new_cost_centers: int
    page: PageInfo


class ImportErrorItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    row_number: int
    field: str
    code: str
    message: str
    raw_value_redacted: str
    severity: str


class ImportErrorListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ImportErrorItem]
    page: PageInfo


class VarianceMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    budget_amount: str
    actual_amount: str
    variance_amount: str
    variance_percent: str | None
    variance_state: str
    favorability: str


class VarianceScopeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fiscal_year: int
    period_from: date
    period_to: date
    budget_version_id: UUID
    currency: str


class VarianceSummaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scope: VarianceScopeResponse
    metrics: VarianceMetricsResponse


class BreakdownItemResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: str
    group_code: str
    group_name: str
    metrics: VarianceMetricsResponse


class BreakdownListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[BreakdownItemResponse]
    page: PageInfo


class CreateExportRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "export_type": "variance_breakdown",
                "format": "csv",
                "filters": {},
                "group_by": "account",
            }
        },
    )
    export_type: Literal["variance_breakdown"] = "variance_breakdown"
    format: Literal["csv"] = "csv"
    filters: dict[str, Any]
    group_by: Literal["period", "account", "department", "cost_center"] = "account"


class ExportJobResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    export_type: str
    format: str
    filename: str
    status: str
    created_at: datetime
    expires_at: datetime
    download_url: str


class ScenarioRuleRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "sequence": 1,
                "scope": {
                    "period_from": "2026-07-01",
                    "period_to": "2026-12-01",
                    "account_ids": [],
                    "department_ids": ["00000000-0000-0000-0000-000000000002"],
                    "cost_center_ids": [],
                },
                "operation": "percentage_change",
                "value": "0.0500",
            }
        },
    )
    sequence: int
    scope: dict[str, Any]
    operation: Literal["percentage_change", "absolute_change"]
    value: str


class CreateScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    baseline_type: Literal["budget", "actual"] = "budget"
    budget_version_id: UUID | None = None
    fiscal_year: int
    rules: list[ScenarioRuleRequest]


class PatchScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    rules: list[ScenarioRuleRequest] | None = None


class PreviewScenarioRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fiscal_year: int
    period_from: date
    period_to: date
    budget_version_id: UUID
    baseline_type: Literal["budget", "actual"] = "budget"
    account_ids: list[UUID] = Field(default_factory=list[UUID])
    department_ids: list[UUID] = Field(default_factory=list[UUID])
    cost_center_ids: list[UUID] = Field(default_factory=list[UUID])
    rules: list[ScenarioRuleRequest]


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    name: str
    baseline_type: str
    budget_version_id: UUID | None
    fiscal_year: int
    status: str
    created_at: datetime
    updated_at: datetime
    rules: list[dict[str, Any]]


class ScenarioListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ScenarioResponse]
    page: PageInfo


class CreateConversationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)


class ConversationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    title: str
    context_filters: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[ConversationResponse]
    page: PageInfo


class CreateMessageRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "content": "¿Qué cuentas explican el exceso de gasto?",
                "context": {
                    "fiscal_year": 2026,
                    "period_from": "2026-01-01",
                    "period_to": "2026-06-01",
                    "budget_version_id": "00000000-0000-0000-0000-000000000001",
                    "department_ids": ["00000000-0000-0000-0000-000000000002"],
                },
            }
        },
    )
    content: str
    context: dict[str, Any] = Field(default_factory=dict)


class CopilotMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: UUID
    answer: str
    scope: dict[str, Any]
    evidence: list[dict[str, Any]]
    limitations: list[str]
    trace_id: str


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    actor_id: UUID
    action: str
    resource_type: str
    resource_id: UUID
    outcome: str
    metadata: dict[str, Any]
    trace_id: str
    created_at: datetime


class AuditEventListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[AuditEventResponse]
    page: PageInfo


def import_job_response(job: ImportJob, *, include_upload: bool = False) -> ImportJobResponse:
    return ImportJobResponse(
        id=job.id,
        organization_id=job.organization_id,
        import_type=job.import_type.value,
        budget_version_id=job.budget_version_id,
        status=job.status.value,
        original_filename=job.original_filename,
        sha256=job.sha256,
        size_bytes=job.size_bytes,
        template_version=job.template_version,
        mapping=job.mapping_json,
        row_count=job.row_count,
        valid_count=job.valid_count,
        error_count=job.error_count,
        warning_count=job.warning_count,
        period_min=job.period_min,
        period_max=job.period_max,
        valid_amount_total=job.valid_amount_total,
        sheet_name=job.sheet_name,
        failure_code=job.failure_code,
        created_at=job.created_at,
        upload=ImportUploadInfo(
            mode="proxy",
            method="PUT",
            url=f"/api/v1/imports/{job.id}/content",
        )
        if include_upload
        else None,
    )


def import_error_item(issue: ImportIssue) -> ImportErrorItem:
    return ImportErrorItem(
        row_number=issue.row_number,
        field=issue.field,
        code=issue.code,
        message=issue.message,
        raw_value_redacted=issue.raw_value_redacted,
        severity=issue.severity.value,
    )


def metrics_response(metrics: VarianceMetrics) -> VarianceMetricsResponse:
    return VarianceMetricsResponse(
        budget_amount=metrics.budget_amount.as_text(),
        actual_amount=metrics.actual_amount.as_text(),
        variance_amount=metrics.variance_amount.as_text(),
        variance_percent=metrics.variance_percent,
        variance_state=metrics.variance_state,
        favorability=metrics.favorability,
    )


def summary_response(summary: VarianceSummary) -> VarianceSummaryResponse:
    return VarianceSummaryResponse(
        scope=VarianceScopeResponse(
            fiscal_year=summary.query.fiscal_year,
            period_from=summary.query.period_from,
            period_to=summary.query.period_to,
            budget_version_id=summary.query.budget_version_id,
            currency=summary.currency,
        ),
        metrics=metrics_response(summary.metrics),
    )


def breakdown_item_response(item: BreakdownItem) -> BreakdownItemResponse:
    return BreakdownItemResponse(
        group_id=item.group_id,
        group_code=item.group_code,
        group_name=item.group_name,
        metrics=metrics_response(item.metrics),
    )


def export_job_response(job: ExportJob) -> ExportJobResponse:
    return ExportJobResponse(
        id=job.id,
        export_type=job.export_type.value,
        format=job.format,
        filename=job.filename,
        status=job.status.value,
        created_at=job.created_at,
        expires_at=job.expires_at,
        download_url=f"/api/v1/exports/{job.id}/content",
    )


def scenario_response(scenario: Scenario) -> ScenarioResponse:
    return ScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        baseline_type=scenario.baseline_type.value,
        budget_version_id=scenario.budget_version_id,
        fiscal_year=scenario.fiscal_year,
        status=scenario.status.value,
        created_at=scenario.created_at,
        updated_at=scenario.updated_at,
        rules=[
            {
                "sequence": rule.sequence,
                "operation": rule.operation.value,
                "value": str(rule.value),
                "scope": {
                    "period_from": rule.scope.period_from.isoformat(),
                    "period_to": rule.scope.period_to.isoformat(),
                    "account_ids": [str(item) for item in rule.scope.account_ids],
                    "department_ids": [str(item) for item in rule.scope.department_ids],
                    "cost_center_ids": [str(item) for item in rule.scope.cost_center_ids],
                },
            }
            for rule in scenario.rules
        ],
    )


def conversation_response(conversation: Conversation) -> ConversationResponse:
    return ConversationResponse(
        id=conversation.id,
        title=conversation.title,
        context_filters=conversation.context_filters,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def copilot_response(answer: CopilotAnswer) -> CopilotMessageResponse:
    return CopilotMessageResponse(
        message_id=answer.message_id,
        answer=answer.answer,
        scope=answer.scope,
        evidence=answer.evidence,
        limitations=answer.limitations,
        trace_id=answer.trace_id,
    )


def audit_event_response(event: AuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        id=event.id,
        actor_id=event.actor_id,
        action=event.action,
        resource_type=event.resource_type,
        resource_id=event.resource_id,
        outcome=event.outcome,
        metadata=sanitized_metadata(event.metadata),
        trace_id=event.trace_id,
        created_at=event.created_at,
    )


def scenario_type(value: str) -> ScenarioType:
    return ScenarioType(value)
