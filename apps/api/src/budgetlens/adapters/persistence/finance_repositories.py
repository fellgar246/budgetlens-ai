from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, case, delete, distinct, func, literal, or_, select, tuple_
from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.mapping import (
    apply_ai_run,
    apply_conversation,
    apply_export_job,
    apply_financial_entry,
    apply_import_job,
    apply_message,
    apply_scenario,
    apply_scenario_rule,
    apply_tool_execution,
    conversation_from_row,
    export_job_from_row,
    import_issue_from_row,
    import_job_from_row,
    message_from_row,
    scenario_from_rows,
)
from budgetlens.adapters.persistence.models import (
    AccountRow,
    AiRunRow,
    ConversationRow,
    CostCenterRow,
    DepartmentRow,
    ExportJobRow,
    FinancialEntryRow,
    ImportErrorRow,
    ImportJobRow,
    MessageRow,
    OrganizationRow,
    ScenarioRow,
    ScenarioRuleRow,
    ToolExecutionRow,
)
from budgetlens.adapters.tenancy import require_tenant_id
from budgetlens.application.analytics_query import AnalyticsQuery, parse_account_types
from budgetlens.application.pagination import Page, decode_cursor, encode_cursor
from budgetlens.domain.conversation import AiRun, Conversation, ConversationMessage, ToolExecution
from budgetlens.domain.enums import AccountType, AnalyticsGroupBy
from budgetlens.domain.errors import ValidationError
from budgetlens.domain.exporting import ExportJob
from budgetlens.domain.financial_entry import FinancialEntry
from budgetlens.domain.identities import IdFactory
from budgetlens.domain.importing import ImportIssue, ImportJob
from budgetlens.domain.money import MoneyAmount
from budgetlens.domain.scenario import Scenario


class SqlImportJobRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = require_tenant_id(organization_id)

    def get(self, job_id: UUID) -> ImportJob | None:
        row = self._session.get(ImportJobRow, job_id)
        if row is None or row.organization_id != self._organization_id:
            return None
        return import_job_from_row(row)

    def get_by_fingerprint(self, fingerprint: str) -> ImportJob | None:
        row = self._session.scalar(
            select(ImportJobRow).where(
                ImportJobRow.organization_id == self._organization_id,
                ImportJobRow.idempotency_fingerprint == fingerprint,
                ImportJobRow.status.not_in(("cancelled", "failed")),
            )
        )
        return import_job_from_row(row) if row else None

    def add(self, job: ImportJob) -> None:
        row = ImportJobRow()
        apply_import_job(row, job)
        self._session.add(row)

    def save(self, job: ImportJob) -> None:
        row = self._session.get(ImportJobRow, job.id)
        if row is None or row.organization_id != self._organization_id:
            self.add(job)
            return
        apply_import_job(row, job)

    def list_page(self, *, cursor: str | None, limit: int) -> Page[ImportJob]:
        stmt = (
            select(ImportJobRow)
            .where(ImportJobRow.organization_id == self._organization_id)
            .order_by(ImportJobRow.created_at.desc(), ImportJobRow.id.desc())
        )
        parsed = decode_cursor(cursor)
        if parsed is not None:
            created_at = datetime.fromisoformat(parsed["created_at"])
            last_id = UUID(parsed["id"])
            stmt = stmt.where(
                or_(
                    ImportJobRow.created_at < created_at,
                    and_(ImportJobRow.created_at == created_at, ImportJobRow.id < last_id),
                )
            )
        rows = list(self._session.scalars(stmt.limit(limit + 1)).all())
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor(
                {"created_at": last.created_at.isoformat(), "id": str(last.id)}
            )
        return Page(
            items=[import_job_from_row(row) for row in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )


def get_import_job(session: Session, job_id: UUID) -> ImportJob | None:
    row = session.get(ImportJobRow, job_id)
    return import_job_from_row(row) if row else None


def list_stale_processing(session: Session, *, cutoff: datetime) -> list[ImportJob]:
    rows = session.scalars(
        select(ImportJobRow).where(
            ImportJobRow.status == "processing",
            ImportJobRow.started_at.is_not(None),
            ImportJobRow.started_at <= cutoff,
        )
    ).all()
    return [import_job_from_row(row) for row in rows]


def list_expired_conversations(session: Session, *, now: datetime) -> list[Conversation]:
    candidates = list(
        session.scalars(select(ConversationRow).where(ConversationRow.deleted_at.is_(None))).all()
    )
    orgs = {
        row.id: row.conversation_retention_days
        for row in session.scalars(select(OrganizationRow)).all()
    }
    expired: list[Conversation] = []
    for row in candidates:
        days = orgs.get(row.organization_id, 90)
        if row.updated_at <= now - timedelta(days=days):
            expired.append(conversation_from_row(row))
    return expired


def list_jobs_with_expired_originals(session: Session, *, cutoff: datetime) -> list[ImportJob]:
    rows = session.scalars(
        select(ImportJobRow).where(
            ImportJobRow.object_key.is_not(None),
            ImportJobRow.created_at <= cutoff,
            ImportJobRow.status.in_(("applied", "cancelled", "failed")),
        )
    ).all()
    return [import_job_from_row(row) for row in rows]


def list_jobs_with_expired_error_reports(session: Session, *, cutoff: datetime) -> list[ImportJob]:
    job_ids = session.scalars(select(ImportErrorRow.import_job_id).distinct()).all()
    if not job_ids:
        return []
    rows = session.scalars(
        select(ImportJobRow).where(
            ImportJobRow.id.in_(job_ids),
            ImportJobRow.created_at <= cutoff,
        )
    ).all()
    return [import_job_from_row(row) for row in rows]


def list_expired_exports(session: Session, *, now: datetime) -> list[ExportJob]:
    rows = session.scalars(
        select(ExportJobRow).where(
            ExportJobRow.status != "expired",
            ExportJobRow.expires_at <= now,
        )
    ).all()
    return [export_job_from_row(row) for row in rows]


class SqlImportErrorRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = require_tenant_id(organization_id)

    def replace_for_job(self, job_id: UUID, issues: list[ImportIssue], *, ids: IdFactory) -> None:
        self._session.execute(
            delete(ImportErrorRow).where(
                ImportErrorRow.organization_id == self._organization_id,
                ImportErrorRow.import_job_id == job_id,
            )
        )
        for issue in issues:
            self._session.add(
                ImportErrorRow(
                    id=ids.new_id(),
                    organization_id=self._organization_id,
                    import_job_id=job_id,
                    row_number=issue.row_number,
                    field=issue.field,
                    code=issue.code,
                    message_safe=issue.message[:240],
                    raw_value_redacted=issue.raw_value_redacted[:80],
                    severity=issue.severity.value,
                )
            )

    def list_page(self, job_id: UUID, *, cursor: str | None, limit: int) -> Page[ImportIssue]:
        stmt = (
            select(ImportErrorRow)
            .where(
                ImportErrorRow.organization_id == self._organization_id,
                ImportErrorRow.import_job_id == job_id,
            )
            .order_by(ImportErrorRow.row_number, ImportErrorRow.field, ImportErrorRow.id)
        )
        parsed = decode_cursor(cursor)
        if parsed is not None:
            stmt = stmt.where(
                or_(
                    ImportErrorRow.row_number > int(parsed["row_number"]),
                    and_(
                        ImportErrorRow.row_number == int(parsed["row_number"]),
                        ImportErrorRow.id > UUID(parsed["id"]),
                    ),
                )
            )
        rows = list(self._session.scalars(stmt.limit(limit + 1)).all())
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor({"row_number": str(last.row_number), "id": str(last.id)})
        return Page(
            items=[import_issue_from_row(row) for row in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def list_all(self, job_id: UUID) -> list[ImportIssue]:
        rows = self._session.scalars(
            select(ImportErrorRow)
            .where(
                ImportErrorRow.organization_id == self._organization_id,
                ImportErrorRow.import_job_id == job_id,
            )
            .order_by(ImportErrorRow.row_number, ImportErrorRow.field)
        ).all()
        return [import_issue_from_row(row) for row in rows]

    def delete_for_job(self, job_id: UUID) -> None:
        self._session.execute(
            delete(ImportErrorRow).where(
                ImportErrorRow.organization_id == self._organization_id,
                ImportErrorRow.import_job_id == job_id,
            )
        )


class SqlFinancialEntryRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = require_tenant_id(organization_id)

    def add(self, entry: FinancialEntry) -> None:
        row = FinancialEntryRow()
        apply_financial_entry(row, entry)
        self._session.add(row)

    def add_many(self, entries: list[FinancialEntry]) -> None:
        for entry in entries:
            self.add(entry)

    def count_for_job(self, job_id: UUID) -> int:
        return len(
            list(
                self._session.scalars(
                    select(FinancialEntryRow.id).where(
                        FinancialEntryRow.organization_id == self._organization_id,
                        FinancialEntryRow.import_job_id == job_id,
                    )
                ).all()
            )
        )

    def count_matching(
        self,
        *,
        scenario_type: str,
        budget_version_id: UUID | None,
        keys: Sequence[tuple[object, object, object, object]],
    ) -> int:
        if not keys:
            return 0
        typed: list[tuple[date, UUID, UUID, UUID]] = []
        for period_start, account_id, department_id, cost_center_id in keys:
            if (
                isinstance(period_start, date)
                and isinstance(account_id, UUID)
                and isinstance(department_id, UUID)
                and isinstance(cost_center_id, UUID)
            ):
                typed.append((period_start, account_id, department_id, cost_center_id))
        if not typed:
            return 0
        version_filter = (
            FinancialEntryRow.budget_version_id == budget_version_id
            if budget_version_id is not None
            else FinancialEntryRow.budget_version_id.is_(None)
        )
        counted = self._session.scalar(
            select(func.count())
            .select_from(FinancialEntryRow)
            .where(
                FinancialEntryRow.organization_id == self._organization_id,
                FinancialEntryRow.scenario_type == scenario_type,
                version_filter,
                tuple_(
                    FinancialEntryRow.period_start,
                    FinancialEntryRow.account_id,
                    FinancialEntryRow.department_id,
                    FinancialEntryRow.cost_center_id,
                ).in_(typed),
            )
        )
        return int(counted or 0)


class SqlScenarioRepository:
    def __init__(self, session: Session, organization_id: UUID, ids: IdFactory) -> None:
        self._session = session
        self._organization_id = require_tenant_id(organization_id)
        self._ids = ids

    def get(self, scenario_id: UUID) -> Scenario | None:
        row = self._session.get(ScenarioRow, scenario_id)
        if row is None or row.organization_id != self._organization_id:
            return None
        rules = list(
            self._session.scalars(
                select(ScenarioRuleRow).where(ScenarioRuleRow.scenario_id == scenario_id)
            ).all()
        )
        return scenario_from_rows(row, rules)

    def add(self, scenario: Scenario) -> None:
        row = ScenarioRow()
        apply_scenario(row, scenario)
        self._session.add(row)
        self._write_rules(scenario)

    def save(self, scenario: Scenario) -> None:
        row = self._session.get(ScenarioRow, scenario.id)
        if row is None or row.organization_id != self._organization_id:
            self.add(scenario)
            return
        apply_scenario(row, scenario)
        self._session.execute(
            delete(ScenarioRuleRow).where(ScenarioRuleRow.scenario_id == scenario.id)
        )
        self._write_rules(scenario)

    def list_page(self, *, cursor: str | None, limit: int) -> Page[Scenario]:
        stmt = (
            select(ScenarioRow)
            .where(ScenarioRow.organization_id == self._organization_id)
            .order_by(ScenarioRow.created_at.desc(), ScenarioRow.id.desc())
        )
        parsed = decode_cursor(cursor)
        if parsed is not None:
            created_at = datetime.fromisoformat(parsed["created_at"])
            last_id = UUID(parsed["id"])
            stmt = stmt.where(
                or_(
                    ScenarioRow.created_at < created_at,
                    and_(ScenarioRow.created_at == created_at, ScenarioRow.id < last_id),
                )
            )
        rows = list(self._session.scalars(stmt.limit(limit + 1)).all())
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        items = [self.get(row.id) for row in page_rows]
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor(
                {"created_at": last.created_at.isoformat(), "id": str(last.id)}
            )
        return Page(
            items=[item for item in items if item is not None],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def _write_rules(self, scenario: Scenario) -> None:
        for rule in scenario.rules:
            row = ScenarioRuleRow()
            apply_scenario_rule(row, scenario=scenario, rule=rule, rule_id=self._ids.new_id())
            self._session.add(row)


class SqlExportJobRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = require_tenant_id(organization_id)

    def get(self, export_id: UUID) -> ExportJob | None:
        row = self._session.get(ExportJobRow, export_id)
        if row is None or row.organization_id != self._organization_id:
            return None
        return export_job_from_row(row)

    def add(self, job: ExportJob) -> None:
        row = ExportJobRow()
        apply_export_job(row, job)
        self._session.add(row)

    def save(self, job: ExportJob) -> None:
        row = self._session.get(ExportJobRow, job.id)
        if row is None or row.organization_id != self._organization_id:
            self.add(job)
            return
        apply_export_job(row, job)


class SqlConversationRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = require_tenant_id(organization_id)

    def get(self, conversation_id: UUID) -> Conversation | None:
        row = self._session.get(ConversationRow, conversation_id)
        if row is None or row.organization_id != self._organization_id:
            return None
        return conversation_from_row(row)

    def add(self, conversation: Conversation) -> None:
        conversation.assert_same_organization(self._organization_id)
        row = ConversationRow()
        apply_conversation(row, conversation)
        self._session.add(row)

    def save(self, conversation: Conversation) -> None:
        conversation.assert_same_organization(self._organization_id)
        row = self._session.get(ConversationRow, conversation.id)
        if row is None:
            self.add(conversation)
            return
        if row.organization_id != self._organization_id:
            raise ValidationError(
                "CONVERSATION_ORG_MISMATCH",
                "Una conversación no se mueve entre organizaciones.",
            )
        apply_conversation(row, conversation)

    def list_page(self, *, user_id: UUID, cursor: str | None, limit: int) -> Page[Conversation]:
        stmt = (
            select(ConversationRow)
            .where(
                ConversationRow.organization_id == self._organization_id,
                ConversationRow.user_id == user_id,
                ConversationRow.deleted_at.is_(None),
            )
            .order_by(ConversationRow.updated_at.desc(), ConversationRow.id.desc())
        )
        parsed = decode_cursor(cursor)
        if parsed is not None:
            updated_at = datetime.fromisoformat(parsed["updated_at"])
            last_id = UUID(parsed["id"])
            stmt = stmt.where(
                or_(
                    ConversationRow.updated_at < updated_at,
                    and_(ConversationRow.updated_at == updated_at, ConversationRow.id < last_id),
                )
            )
        rows = list(self._session.scalars(stmt.limit(limit + 1)).all())
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor(
                {"updated_at": last.updated_at.isoformat(), "id": str(last.id)}
            )
        return Page(
            items=[conversation_from_row(row) for row in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    def add_message(self, message: ConversationMessage) -> None:
        if message.organization_id != self._organization_id:
            raise ValidationError(
                "CONVERSATION_ORG_MISMATCH",
                "Una conversación no se mueve entre organizaciones.",
            )
        row = MessageRow()
        apply_message(row, message)
        self._session.add(row)

    def list_messages(self, conversation_id: UUID, *, limit: int = 12) -> list[ConversationMessage]:
        rows = list(
            self._session.scalars(
                select(MessageRow)
                .where(
                    MessageRow.organization_id == self._organization_id,
                    MessageRow.conversation_id == conversation_id,
                )
                .order_by(MessageRow.created_at.desc(), MessageRow.id.desc())
                .limit(limit)
            ).all()
        )
        return [message_from_row(row) for row in reversed(rows)]

    def add_run(self, run: AiRun) -> None:
        row = AiRunRow()
        apply_ai_run(row, run)
        self._session.add(row)

    def add_tool(self, execution: ToolExecution) -> None:
        row = ToolExecutionRow()
        apply_tool_execution(row, execution)
        self._session.add(row)


@dataclass(frozen=True, slots=True)
class AggregatedTotals:
    budget_amount: MoneyAmount
    actual_amount: MoneyAmount
    account_types: list[AccountType]


@dataclass(frozen=True, slots=True)
class GroupedTotals:
    group_id: str
    group_code: str
    group_name: str
    budget_amount: MoneyAmount
    actual_amount: MoneyAmount
    account_types: list[AccountType]


class SqlAnalyticsRepository:
    """Tenant-scoped SQL aggregates. Callers never load raw financial rows for a summary."""

    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = require_tenant_id(organization_id)

    def totals(self, query: AnalyticsQuery) -> AggregatedTotals:
        row = self._session.execute(self.totals_statement(query)).one()
        return AggregatedTotals(
            budget_amount=MoneyAmount(row.budget_amount or 0),
            actual_amount=MoneyAmount(row.actual_amount or 0),
            account_types=parse_account_types(row.account_types),
        )

    def grouped_totals(
        self, query: AnalyticsQuery, group_by: AnalyticsGroupBy
    ) -> list[GroupedTotals]:
        group_id, group_code, group_name = _group_columns(group_by)
        rows = self._session.execute(
            self._grouped_statement(query, group_id, group_code, group_name)
        ).all()
        return [
            GroupedTotals(
                group_id=str(row.group_id),
                group_code=str(row.group_code),
                group_name=str(row.group_name),
                budget_amount=MoneyAmount(row.budget_amount or 0),
                actual_amount=MoneyAmount(row.actual_amount or 0),
                account_types=parse_account_types(row.account_types),
            )
            for row in rows
        ]

    def totals_statement(self, query: AnalyticsQuery) -> Select[Any]:
        stmt = select(
            *_amount_columns(query),
            func.array_agg(distinct(AccountRow.account_type)).label("account_types"),
        )
        return self._apply_filters(stmt, query).join(
            AccountRow,
            and_(
                AccountRow.id == FinancialEntryRow.account_id,
                AccountRow.organization_id == FinancialEntryRow.organization_id,
            ),
        )

    def _grouped_statement(
        self,
        query: AnalyticsQuery,
        group_id: Any,
        group_code: Any,
        group_name: Any,
    ) -> Select[Any]:
        stmt = select(
            group_id.label("group_id"),
            group_code.label("group_code"),
            group_name.label("group_name"),
            *_amount_columns(query),
            func.array_agg(distinct(AccountRow.account_type)).label("account_types"),
        )
        stmt = self._apply_filters(stmt, query)
        stmt = stmt.join(
            AccountRow,
            and_(
                AccountRow.id == FinancialEntryRow.account_id,
                AccountRow.organization_id == FinancialEntryRow.organization_id,
            ),
        )
        if group_id is DepartmentRow.id:
            stmt = stmt.join(
                DepartmentRow,
                and_(
                    DepartmentRow.id == FinancialEntryRow.department_id,
                    DepartmentRow.organization_id == FinancialEntryRow.organization_id,
                ),
            )
        if group_id is CostCenterRow.id:
            stmt = stmt.join(
                CostCenterRow,
                and_(
                    CostCenterRow.id == FinancialEntryRow.cost_center_id,
                    CostCenterRow.organization_id == FinancialEntryRow.organization_id,
                ),
            )
        return stmt.group_by(group_id, group_code, group_name)

    def _apply_filters(self, stmt: Select[Any], query: AnalyticsQuery) -> Select[Any]:
        stmt = stmt.where(
            FinancialEntryRow.organization_id == self._organization_id,
            FinancialEntryRow.fiscal_year == query.fiscal_year,
            FinancialEntryRow.period_start >= query.period_from,
            FinancialEntryRow.period_start <= query.period_to,
            or_(
                and_(
                    FinancialEntryRow.scenario_type == "budget",
                    FinancialEntryRow.budget_version_id == query.budget_version_id,
                ),
                FinancialEntryRow.scenario_type == "actual",
            ),
        )
        if query.account_ids:
            stmt = stmt.where(FinancialEntryRow.account_id.in_(query.account_ids))
        if query.department_ids:
            stmt = stmt.where(FinancialEntryRow.department_id.in_(query.department_ids))
        if query.cost_center_ids:
            stmt = stmt.where(FinancialEntryRow.cost_center_id.in_(query.cost_center_ids))
        return stmt


def _amount_columns(query: AnalyticsQuery) -> tuple[Any, Any]:
    return (
        func.coalesce(
            func.sum(
                case(
                    (
                        and_(
                            FinancialEntryRow.scenario_type == "budget",
                            FinancialEntryRow.budget_version_id == query.budget_version_id,
                        ),
                        FinancialEntryRow.amount,
                    ),
                    else_=literal(0),
                )
            ),
            0,
        ).label("budget_amount"),
        func.coalesce(
            func.sum(
                case(
                    (FinancialEntryRow.scenario_type == "actual", FinancialEntryRow.amount),
                    else_=literal(0),
                )
            ),
            0,
        ).label("actual_amount"),
    )


def _group_columns(group_by: AnalyticsGroupBy) -> tuple[Any, Any, Any]:
    if group_by is AnalyticsGroupBy.PERIOD:
        return (
            FinancialEntryRow.period_start,
            FinancialEntryRow.period_start,
            FinancialEntryRow.period_start,
        )
    if group_by is AnalyticsGroupBy.ACCOUNT:
        return AccountRow.id, AccountRow.code, AccountRow.name
    if group_by is AnalyticsGroupBy.DEPARTMENT:
        return DepartmentRow.id, DepartmentRow.code, DepartmentRow.name
    return CostCenterRow.id, CostCenterRow.code, CostCenterRow.name
