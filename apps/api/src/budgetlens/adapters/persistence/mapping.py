from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from budgetlens.adapters.persistence.models import (
    AccountRow,
    AiRunRow,
    AuditEventRow,
    BudgetVersionRow,
    ConversationRow,
    CostCenterRow,
    DepartmentRow,
    ExportJobRow,
    FinancialEntryRow,
    ImportErrorRow,
    ImportJobRow,
    MembershipRow,
    MessageRow,
    OrganizationRow,
    ScenarioRow,
    ScenarioRuleRow,
    ToolExecutionRow,
    UserRow,
)
from budgetlens.domain.audit import AuditEvent
from budgetlens.domain.budget_version import BudgetVersion
from budgetlens.domain.conversation import AiRun, Conversation, ConversationMessage, ToolExecution
from budgetlens.domain.dimensions import Account, CostCenter, Department
from budgetlens.domain.enums import (
    AccountType,
    BudgetVersionStatus,
    DimensionStatus,
    ExportJobStatus,
    ExportType,
    ImportErrorSeverity,
    ImportJobStatus,
    MembershipStatus,
    MessageRole,
    OrganizationStatus,
    PlatformRole,
    Role,
    ScenarioOperation,
    ScenarioStatus,
    ScenarioType,
    UserStatus,
)
from budgetlens.domain.exporting import ExportJob
from budgetlens.domain.financial_entry import FinancialEntry
from budgetlens.domain.importing import ImportIssue, ImportJob
from budgetlens.domain.money import Currency, MoneyAmount
from budgetlens.domain.organization import Membership, Organization, User
from budgetlens.domain.scenario import Scenario, ScenarioRule, ScenarioScope


def user_from_row(row: UserRow) -> User:
    return User(
        id=row.id,
        email=str(row.email),
        display_name=row.display_name,
        status=UserStatus(row.status),
        external_subject=row.external_subject,
        created_at=row.created_at,
        updated_at=row.updated_at,
        platform_role=PlatformRole(row.platform_role) if row.platform_role else None,
    )


def apply_user(row: UserRow, entity: User) -> None:
    row.id = entity.id
    row.email = entity.email
    row.display_name = entity.display_name
    row.status = entity.status.value
    row.external_subject = entity.external_subject
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at
    row.platform_role = entity.platform_role.value if entity.platform_role else None


def organization_from_row(row: OrganizationRow) -> Organization:
    return Organization(
        id=row.id,
        name=row.name,
        slug=row.slug,
        functional_currency=Currency(row.functional_currency),
        fiscal_year_start_month=row.fiscal_year_start_month,
        status=OrganizationStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version,
    )


def apply_organization(row: OrganizationRow, entity: Organization) -> None:
    row.id = entity.id
    row.name = entity.name
    row.slug = entity.slug
    row.functional_currency = entity.functional_currency.code
    row.fiscal_year_start_month = entity.fiscal_year_start_month
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at
    row.version = entity.version


def membership_from_row(row: MembershipRow) -> Membership:
    return Membership(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        role=Role(row.role),
        status=MembershipStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def apply_membership(row: MembershipRow, entity: Membership) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.user_id = entity.user_id
    row.role = entity.role.value
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at


def account_from_row(row: AccountRow) -> Account:
    return Account(
        id=row.id,
        organization_id=row.organization_id,
        code=row.code,
        name=row.name,
        account_type=AccountType(row.account_type),
        parent_id=row.parent_id,
        status=DimensionStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def apply_account(row: AccountRow, entity: Account) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.code = entity.code
    row.name = entity.name
    row.account_type = entity.account_type.value
    row.parent_id = entity.parent_id
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at


def department_from_row(row: DepartmentRow) -> Department:
    return Department(
        id=row.id,
        organization_id=row.organization_id,
        code=row.code,
        name=row.name,
        status=DimensionStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def apply_department(row: DepartmentRow, entity: Department) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.code = entity.code
    row.name = entity.name
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at


def cost_center_from_row(row: CostCenterRow) -> CostCenter:
    return CostCenter(
        id=row.id,
        organization_id=row.organization_id,
        code=row.code,
        name=row.name,
        status=DimensionStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def apply_cost_center(row: CostCenterRow, entity: CostCenter) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.code = entity.code
    row.name = entity.name
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at


def budget_version_from_row(row: BudgetVersionRow) -> BudgetVersion:
    return BudgetVersion(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        fiscal_year=row.fiscal_year,
        status=BudgetVersionStatus(row.status),
        is_active=row.is_active,
        published_at=row.published_at,
        published_by=row.published_by,
        created_at=row.created_at,
        version=row.version,
    )


def apply_budget_version(row: BudgetVersionRow, entity: BudgetVersion) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.name = entity.name
    row.fiscal_year = entity.fiscal_year
    row.status = entity.status.value
    row.is_active = entity.is_active
    row.published_at = entity.published_at
    row.published_by = entity.published_by
    row.created_at = entity.created_at
    row.version = entity.version


def audit_from_row(row: AuditEventRow) -> AuditEvent:
    return AuditEvent(
        id=row.id,
        organization_id=row.organization_id,
        actor_id=row.actor_id,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        outcome=row.outcome,
        metadata=dict(row.metadata_json),
        trace_id=row.trace_id,
        created_at=row.created_at,
        schema_version=row.schema_version,
    )


def apply_audit(row: AuditEventRow, entity: AuditEvent) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.actor_id = entity.actor_id
    row.action = entity.action
    row.resource_type = entity.resource_type
    row.resource_id = entity.resource_id
    row.outcome = entity.outcome
    row.metadata_json = entity.metadata
    row.trace_id = entity.trace_id
    row.created_at = entity.created_at
    row.schema_version = entity.schema_version
    row.ip_hash = None


def import_job_from_row(row: ImportJobRow) -> ImportJob:
    return ImportJob(
        id=row.id,
        organization_id=row.organization_id,
        created_by=row.created_by,
        import_type=ScenarioType(row.import_type),
        budget_version_id=row.budget_version_id,
        status=ImportJobStatus(row.status),
        original_filename=row.original_filename,
        object_key=row.object_key,
        sha256=row.sha256,
        size_bytes=int(row.size_bytes),
        media_type=row.media_type,
        template_version=row.template_version,
        mapping_json=dict(row.mapping_json),
        row_count=row.row_count,
        valid_count=row.valid_count,
        error_count=row.error_count,
        warning_count=row.warning_count,
        period_min=row.period_min,
        period_max=row.period_max,
        valid_amount_total=row.valid_amount_total,
        idempotency_fingerprint=row.idempotency_fingerprint,
        started_at=row.started_at,
        completed_at=row.completed_at,
        created_at=row.created_at,
        failure_code=row.failure_code,
        create_missing_dimensions=row.create_missing_dimensions,
        sheet_name=row.sheet_name,
    )


def apply_import_job(row: ImportJobRow, entity: ImportJob) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.created_by = entity.created_by
    row.import_type = entity.import_type.value
    row.budget_version_id = entity.budget_version_id
    row.status = entity.status.value
    row.original_filename = entity.original_filename
    row.object_key = entity.object_key
    row.sha256 = entity.sha256
    row.size_bytes = entity.size_bytes
    row.media_type = entity.media_type
    row.template_version = entity.template_version
    row.mapping_json = entity.mapping_json
    row.row_count = entity.row_count
    row.valid_count = entity.valid_count
    row.error_count = entity.error_count
    row.warning_count = entity.warning_count
    row.period_min = entity.period_min
    row.period_max = entity.period_max
    row.valid_amount_total = entity.valid_amount_total
    row.idempotency_fingerprint = entity.idempotency_fingerprint
    row.started_at = entity.started_at
    row.completed_at = entity.completed_at
    row.created_at = entity.created_at
    row.failure_code = entity.failure_code
    row.create_missing_dimensions = entity.create_missing_dimensions
    row.sheet_name = entity.sheet_name


def import_issue_from_row(row: ImportErrorRow) -> ImportIssue:
    return ImportIssue(
        row_number=row.row_number,
        field=row.field,
        code=row.code,
        message=row.message_safe,
        raw_value_redacted=row.raw_value_redacted,
        severity=ImportErrorSeverity(row.severity),
    )


def financial_entry_from_row(row: FinancialEntryRow) -> FinancialEntry:
    return FinancialEntry(
        id=row.id,
        organization_id=row.organization_id,
        import_job_id=row.import_job_id,
        scenario_type=ScenarioType(row.scenario_type),
        budget_version_id=row.budget_version_id,
        period_start=row.period_start,
        fiscal_year=row.fiscal_year,
        account_id=row.account_id,
        department_id=row.department_id,
        cost_center_id=row.cost_center_id,
        amount=MoneyAmount(row.amount),
        currency=Currency(row.currency),
        source_row_number=row.source_row_number,
        source_reference=row.source_reference,
        created_at=row.created_at,
    )


def apply_financial_entry(row: FinancialEntryRow, entity: FinancialEntry) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.import_job_id = entity.import_job_id
    row.scenario_type = entity.scenario_type.value
    row.budget_version_id = entity.budget_version_id
    row.period_start = entity.period_start
    row.fiscal_year = entity.fiscal_year
    row.account_id = entity.account_id
    row.department_id = entity.department_id
    row.cost_center_id = entity.cost_center_id
    row.amount = entity.amount.value
    row.currency = entity.currency.code
    row.source_row_number = entity.source_row_number
    row.source_reference = entity.source_reference
    row.created_at = entity.created_at


def _scope_from_json(payload: dict[str, Any]) -> ScenarioScope:
    return ScenarioScope(
        period_from=date.fromisoformat(str(payload["period_from"])),
        period_to=date.fromisoformat(str(payload["period_to"])),
        account_ids=tuple(UUID(item) for item in payload.get("account_ids", [])),
        department_ids=tuple(UUID(item) for item in payload.get("department_ids", [])),
        cost_center_ids=tuple(UUID(item) for item in payload.get("cost_center_ids", [])),
    )


def _scope_to_json(scope: ScenarioScope) -> dict[str, Any]:
    return {
        "period_from": scope.period_from.isoformat(),
        "period_to": scope.period_to.isoformat(),
        "account_ids": [str(item) for item in scope.account_ids],
        "department_ids": [str(item) for item in scope.department_ids],
        "cost_center_ids": [str(item) for item in scope.cost_center_ids],
    }


def scenario_from_rows(row: ScenarioRow, rules: list[ScenarioRuleRow]) -> Scenario:
    return Scenario(
        id=row.id,
        organization_id=row.organization_id,
        created_by=row.created_by,
        name=row.name,
        baseline_type=ScenarioType(row.baseline_type),
        budget_version_id=row.budget_version_id,
        fiscal_year=row.fiscal_year,
        status=ScenarioStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        rules=tuple(
            ScenarioRule(
                sequence=item.sequence,
                operation=ScenarioOperation(item.operation),
                value=Decimal(item.value),
                scope=_scope_from_json(item.scope_json),
            )
            for item in sorted(rules, key=lambda current: current.sequence)
        ),
    )


def apply_scenario(row: ScenarioRow, entity: Scenario) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.created_by = entity.created_by
    row.name = entity.name
    row.baseline_type = entity.baseline_type.value
    row.budget_version_id = entity.budget_version_id
    row.fiscal_year = entity.fiscal_year
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at


def apply_scenario_rule(
    row: ScenarioRuleRow, *, scenario: Scenario, rule: ScenarioRule, rule_id: UUID
) -> None:
    row.id = rule_id
    row.organization_id = scenario.organization_id
    row.scenario_id = scenario.id
    row.sequence = rule.sequence
    row.scope_json = _scope_to_json(rule.scope)
    row.operation = rule.operation.value
    row.value = rule.value


def export_job_from_row(row: ExportJobRow) -> ExportJob:
    return ExportJob(
        id=row.id,
        organization_id=row.organization_id,
        created_by=row.created_by,
        export_type=ExportType(row.export_type),
        format=row.format,
        filters_json=dict(row.filters_json),
        object_key=row.object_key,
        filename=row.filename,
        status=ExportJobStatus(row.status),
        created_at=row.created_at,
        expires_at=row.expires_at,
    )


def apply_export_job(row: ExportJobRow, entity: ExportJob) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.created_by = entity.created_by
    row.export_type = entity.export_type.value
    row.format = entity.format
    row.filters_json = entity.filters_json
    row.object_key = entity.object_key
    row.filename = entity.filename
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.expires_at = entity.expires_at


def conversation_from_row(row: ConversationRow) -> Conversation:
    return Conversation(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        title=row.title,
        context_filters=dict(row.context_filters_json),
        created_at=row.created_at,
        updated_at=row.updated_at,
        deleted_at=row.deleted_at,
    )


def apply_conversation(row: ConversationRow, entity: Conversation) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.user_id = entity.user_id
    row.title = entity.title
    row.context_filters_json = entity.context_filters
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at
    row.deleted_at = entity.deleted_at


def message_from_row(row: MessageRow) -> ConversationMessage:
    return ConversationMessage(
        id=row.id,
        organization_id=row.organization_id,
        conversation_id=row.conversation_id,
        role=MessageRole(row.role),
        content=row.content,
        created_at=row.created_at,
    )


def apply_message(row: MessageRow, entity: ConversationMessage) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.conversation_id = entity.conversation_id
    row.role = entity.role.value
    row.content = entity.content
    row.created_at = entity.created_at


def apply_ai_run(row: AiRunRow, entity: AiRun) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.conversation_id = entity.conversation_id
    row.provider = entity.provider
    row.model_id = entity.model_id
    row.latency_ms = entity.latency_ms
    row.input_units = entity.input_units
    row.output_units = entity.output_units
    row.status = entity.status.value
    row.trace_id = entity.trace_id
    row.created_at = entity.created_at


def apply_tool_execution(row: ToolExecutionRow, entity: ToolExecution) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.ai_run_id = entity.ai_run_id
    row.tool_name = entity.tool_name
    row.argument_hash = entity.argument_hash
    row.result_hash = entity.result_hash
    row.row_count = entity.row_count
    row.duration_ms = entity.duration_ms
    row.status = entity.status.value
