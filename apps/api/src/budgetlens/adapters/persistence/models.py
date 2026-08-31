from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.dialects.postgresql import CITEXT, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from budgetlens.adapters.persistence.base import Base


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("external_subject", name="uq_users_external_subject"),
        CheckConstraint(
            "platform_role IS NULL OR platform_role IN ('operator')",
            name="ck_users_platform_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    external_subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(CITEXT(), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    platform_role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class OrganizationRow(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "fiscal_year_start_month BETWEEN 1 AND 12",
            name="ck_organizations_fiscal_year_start_month",
        ),
        CheckConstraint("status IN ('active', 'archived')", name="ck_organizations_status"),
        CheckConstraint(
            "char_length(functional_currency) = 3",
            name="ck_organizations_functional_currency",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    functional_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fiscal_year_start_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)


class MembershipRow(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_memberships_org_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AccountRow(Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_accounts_org_id"),
        UniqueConstraint("organization_id", "code", name="uq_accounts_org_code"),
        ForeignKeyConstraint(
            ["organization_id", "parent_id"],
            ["accounts.organization_id", "accounts.id"],
            name="fk_accounts_parent_same_org",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DepartmentRow(Base):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_departments_org_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CostCenterRow(Base):
    __tablename__ = "cost_centers"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_cost_centers_org_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BudgetVersionRow(Base):
    __tablename__ = "budget_versions"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "fiscal_year",
            "name",
            name="uq_budget_versions_org_fy_name",
        ),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_budget_versions_status",
        ),
        CheckConstraint(
            "status NOT IN ('published', 'archived') OR published_at IS NOT NULL",
            name="ck_budget_versions_published_at",
        ),
        Index(
            "ux_budget_versions_one_active",
            "organization_id",
            "fiscal_year",
            unique=True,
            postgresql_where="is_active IS TRUE AND status = 'published'",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    published_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)


class AuditEventRow(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=True,
        index=True,
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(40), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False)


class IdempotencyRecordRow(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "user_id",
            "operation",
            "key",
            name="uq_idempotency_scope",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    operation: Mapped[str] = mapped_column(String(80), nullable=False)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SchemaMetaRow(Base):
    __tablename__ = "schema_meta"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ImportJobRow(Base):
    __tablename__ = "import_jobs"
    __table_args__ = (
        UniqueConstraint("organization_id", "id", name="uq_import_jobs_org_id"),
        Index(
            "ux_import_jobs_fingerprint",
            "organization_id",
            "idempotency_fingerprint",
            unique=True,
            postgresql_where=(
                "idempotency_fingerprint IS NOT NULL AND status NOT IN ('cancelled', 'failed')"
            ),
        ),
        CheckConstraint(
            (
                "status IN ('created','uploaded','processing','ready',"
                "'invalid','applied','cancelled','failed')"
            ),
            name="ck_import_jobs_status",
        ),
        CheckConstraint("import_type IN ('budget', 'actual')", name="ck_import_jobs_type"),
        ForeignKeyConstraint(
            ["organization_id", "budget_version_id"],
            ["budget_versions.organization_id", "budget_versions.id"],
            name="fk_import_jobs_budget_version_same_org",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    import_type: Mapped[str] = mapped_column(String(16), nullable=False)
    budget_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    media_type: Mapped[str] = mapped_column(String(128), nullable=False)
    template_version: Mapped[str] = mapped_column(String(20), nullable=False)
    mapping_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    valid_count: Mapped[int] = mapped_column(Integer, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, nullable=False)
    period_min: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_max: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_amount_total: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_fingerprint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    create_missing_dimensions: Mapped[bool] = mapped_column(Boolean, nullable=False)
    sheet_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class ImportErrorRow(Base):
    __tablename__ = "import_errors"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "import_job_id"],
            ["import_jobs.organization_id", "import_jobs.id"],
            name="fk_import_errors_job_same_org",
        ),
        Index("ix_import_errors_job_row", "organization_id", "import_job_id", "row_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    import_job_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    field: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    message_safe: Mapped[str] = mapped_column(String(240), nullable=False)
    raw_value_redacted: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)


class FinancialEntryRow(Base):
    __tablename__ = "financial_entries"
    __table_args__ = (
        CheckConstraint("scenario_type IN ('budget', 'actual')", name="ck_financial_entries_type"),
        CheckConstraint(
            "(scenario_type = 'budget' AND budget_version_id IS NOT NULL) OR "
            "(scenario_type = 'actual' AND budget_version_id IS NULL)",
            name="ck_financial_entries_version",
        ),
        ForeignKeyConstraint(
            ["organization_id", "import_job_id"],
            ["import_jobs.organization_id", "import_jobs.id"],
            name="fk_financial_entries_job_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "account_id"],
            ["accounts.organization_id", "accounts.id"],
            name="fk_financial_entries_account_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            name="fk_financial_entries_department_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "cost_center_id"],
            ["cost_centers.organization_id", "cost_centers.id"],
            name="fk_financial_entries_cost_center_same_org",
        ),
        ForeignKeyConstraint(
            ["organization_id", "budget_version_id"],
            ["budget_versions.organization_id", "budget_versions.id"],
            name="fk_financial_entries_version_same_org",
        ),
        Index(
            "ix_financial_entries_org_fy_period", "organization_id", "fiscal_year", "period_start"
        ),
        Index(
            "ix_financial_entries_org_version_period",
            "organization_id",
            "budget_version_id",
            "period_start",
        ),
        Index(
            "ix_financial_entries_org_account_period",
            "organization_id",
            "account_id",
            "period_start",
        ),
        Index(
            "ix_financial_entries_org_department_period",
            "organization_id",
            "department_id",
            "period_start",
        ),
        Index(
            "ix_financial_entries_org_cost_center_period",
            "organization_id",
            "cost_center_id",
            "period_start",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    import_job_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    scenario_type: Mapped[str] = mapped_column(String(16), nullable=False)
    budget_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    department_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    cost_center_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(160), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScenarioRow(Base):
    __tablename__ = "scenarios"
    __table_args__ = (UniqueConstraint("organization_id", "id", name="uq_scenarios_org_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    baseline_type: Mapped[str] = mapped_column(String(16), nullable=False)
    budget_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    fiscal_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ScenarioRuleRow(Base):
    __tablename__ = "scenario_rules"
    __table_args__ = (
        UniqueConstraint("scenario_id", "sequence", name="uq_scenario_rules_sequence"),
        ForeignKeyConstraint(
            ["organization_id", "scenario_id"],
            ["scenarios.organization_id", "scenarios.id"],
            name="fk_scenario_rules_same_org",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(19, 6), nullable=False)


class ExportJobRow(Base):
    __tablename__ = "export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    export_type: Mapped[str] = mapped_column(String(40), nullable=False)
    format: Mapped[str] = mapped_column(String(16), nullable=False)
    filters_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ConversationRow(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("organization_id", "id", name="uq_conversations_org_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    context_filters_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MessageRow(Base):
    __tablename__ = "messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["organization_id", "conversation_id"],
            ["conversations.organization_id", "conversations.id"],
            name="fk_messages_conversation_same_org",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AiRunRow(Base):
    __tablename__ = "ai_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("conversations.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    input_units: Mapped[int] = mapped_column(Integer, nullable=False)
    output_units: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ToolExecutionRow(Base):
    __tablename__ = "tool_executions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    ai_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("ai_runs.id"), nullable=False
    )
    tool_name: Mapped[str] = mapped_column(String(80), nullable=False)
    argument_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
