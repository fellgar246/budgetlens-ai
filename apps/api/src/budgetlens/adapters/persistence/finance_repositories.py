from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, delete, or_, select
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
    AiRunRow,
    ConversationRow,
    ExportJobRow,
    FinancialEntryRow,
    ImportErrorRow,
    ImportJobRow,
    MessageRow,
    ScenarioRow,
    ScenarioRuleRow,
    ToolExecutionRow,
)
from budgetlens.application.pagination import Page, decode_cursor, encode_cursor
from budgetlens.domain.conversation import AiRun, Conversation, ConversationMessage, ToolExecution
from budgetlens.domain.exporting import ExportJob
from budgetlens.domain.financial_entry import FinancialEntry
from budgetlens.domain.identities import IdFactory
from budgetlens.domain.importing import ImportIssue, ImportJob
from budgetlens.domain.scenario import Scenario


class SqlImportJobRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = organization_id

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


class SqlImportErrorRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = organization_id

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


class SqlFinancialEntryRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = organization_id

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


class SqlScenarioRepository:
    def __init__(self, session: Session, organization_id: UUID, ids: IdFactory) -> None:
        self._session = session
        self._organization_id = organization_id
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
        self._organization_id = organization_id

    def get(self, export_id: UUID) -> ExportJob | None:
        row = self._session.get(ExportJobRow, export_id)
        if row is None or row.organization_id != self._organization_id:
            return None
        return export_job_from_row(row)

    def add(self, job: ExportJob) -> None:
        row = ExportJobRow()
        apply_export_job(row, job)
        self._session.add(row)


class SqlConversationRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = organization_id

    def get(self, conversation_id: UUID) -> Conversation | None:
        row = self._session.get(ConversationRow, conversation_id)
        if row is None or row.organization_id != self._organization_id:
            return None
        return conversation_from_row(row)

    def add(self, conversation: Conversation) -> None:
        row = ConversationRow()
        apply_conversation(row, conversation)
        self._session.add(row)

    def save(self, conversation: Conversation) -> None:
        row = self._session.get(ConversationRow, conversation.id)
        if row is None or row.organization_id != self._organization_id:
            self.add(conversation)
            return
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
