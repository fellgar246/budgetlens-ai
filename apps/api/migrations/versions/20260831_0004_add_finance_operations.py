"""Add import, financial entry, scenario, export, and conversation tables.

Revision ID: 20260831_0004
Revises: 20260831_0003
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260831_0004"
down_revision: str | None = "20260831_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_budget_versions_org_id", "budget_versions", ["organization_id", "id"]
    )
    op.create_unique_constraint("uq_departments_org_id", "departments", ["organization_id", "id"])
    op.create_unique_constraint("uq_cost_centers_org_id", "cost_centers", ["organization_id", "id"])

    op.create_table(
        "import_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("import_type", sa.String(length=16), nullable=False),
        sa.Column("budget_version_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("media_type", sa.String(length=128), nullable=False),
        sa.Column("template_version", sa.String(length=20), nullable=False),
        sa.Column("mapping_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("valid_count", sa.Integer(), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=False),
        sa.Column("warning_count", sa.Integer(), nullable=False),
        sa.Column("period_min", sa.Date(), nullable=True),
        sa.Column("period_max", sa.Date(), nullable=True),
        sa.Column("valid_amount_total", sa.String(length=32), nullable=False),
        sa.Column("idempotency_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("failure_code", sa.String(length=64), nullable=True),
        sa.Column("create_missing_dimensions", sa.Boolean(), nullable=False),
        sa.Column("sheet_name", sa.String(length=160), nullable=True),
        sa.CheckConstraint(
            "status IN ('created','uploaded','ready','invalid','applied','cancelled','failed')",
            name="ck_import_jobs_status",
        ),
        sa.CheckConstraint("import_type IN ('budget', 'actual')", name="ck_import_jobs_type"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "budget_version_id"],
            ["budget_versions.organization_id", "budget_versions.id"],
            name="fk_import_jobs_budget_version_same_org",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_import_jobs_org_id"),
    )
    op.create_index("ix_import_jobs_organization_id", "import_jobs", ["organization_id"])
    op.create_index(
        "ux_import_jobs_fingerprint",
        "import_jobs",
        ["organization_id", "idempotency_fingerprint"],
        unique=True,
        postgresql_where=sa.text(
            "idempotency_fingerprint IS NOT NULL AND status NOT IN ('cancelled', 'failed')"
        ),
    )

    op.create_table(
        "import_errors",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("field", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("message_safe", sa.String(length=240), nullable=False),
        sa.Column("raw_value_redacted", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "import_job_id"],
            ["import_jobs.organization_id", "import_jobs.id"],
            name="fk_import_errors_job_same_org",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_import_errors_job_row",
        "import_errors",
        ["organization_id", "import_job_id", "row_number"],
    )

    op.create_table(
        "financial_entries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_type", sa.String(length=16), nullable=False),
        sa.Column("budget_version_id", sa.Uuid(), nullable=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Uuid(), nullable=False),
        sa.Column("department_id", sa.Uuid(), nullable=False),
        sa.Column("cost_center_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(19, 4), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("source_row_number", sa.Integer(), nullable=False),
        sa.Column("source_reference", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "scenario_type IN ('budget', 'actual')", name="ck_financial_entries_type"
        ),
        sa.CheckConstraint(
            "(scenario_type = 'budget' AND budget_version_id IS NOT NULL) OR "
            "(scenario_type = 'actual' AND budget_version_id IS NULL)",
            name="ck_financial_entries_version",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "import_job_id"],
            ["import_jobs.organization_id", "import_jobs.id"],
            name="fk_financial_entries_job_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "account_id"],
            ["accounts.organization_id", "accounts.id"],
            name="fk_financial_entries_account_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "department_id"],
            ["departments.organization_id", "departments.id"],
            name="fk_financial_entries_department_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "cost_center_id"],
            ["cost_centers.organization_id", "cost_centers.id"],
            name="fk_financial_entries_cost_center_same_org",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "budget_version_id"],
            ["budget_versions.organization_id", "budget_versions.id"],
            name="fk_financial_entries_version_same_org",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_financial_entries_org_fy_period",
        "financial_entries",
        ["organization_id", "fiscal_year", "period_start"],
    )
    op.create_index(
        "ix_financial_entries_org_version_period",
        "financial_entries",
        ["organization_id", "budget_version_id", "period_start"],
    )
    op.create_index(
        "ix_financial_entries_org_account_period",
        "financial_entries",
        ["organization_id", "account_id", "period_start"],
    )
    op.create_index(
        "ix_financial_entries_org_department_period",
        "financial_entries",
        ["organization_id", "department_id", "period_start"],
    )
    op.create_index(
        "ix_financial_entries_org_cost_center_period",
        "financial_entries",
        ["organization_id", "cost_center_id", "period_start"],
    )

    op.create_table(
        "scenarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("baseline_type", sa.String(length=16), nullable=False),
        sa.Column("budget_version_id", sa.Uuid(), nullable=True),
        sa.Column("fiscal_year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_scenarios_org_id"),
    )
    op.create_index("ix_scenarios_organization_id", "scenarios", ["organization_id"])

    op.create_table(
        "scenario_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("scope_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Numeric(19, 6), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "scenario_id"],
            ["scenarios.organization_id", "scenarios.id"],
            name="fk_scenario_rules_same_org",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scenario_id", "sequence", name="uq_scenario_rules_sequence"),
    )

    op.create_table(
        "export_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("export_type", sa.String(length=40), nullable=False),
        sa.Column("format", sa.String(length=16), nullable=False),
        sa.Column("filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_export_jobs_organization_id", "export_jobs", ["organization_id"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("context_filters_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "id", name="uq_conversations_org_id"),
    )
    op.create_index("ix_conversations_organization_id", "conversations", ["organization_id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(
            ["organization_id", "conversation_id"],
            ["conversations.organization_id", "conversations.id"],
            name="fk_messages_conversation_same_org",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ai_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("conversation_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("model_id", sa.String(length=120), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("input_units", sa.Integer(), nullable=False),
        sa.Column("output_units", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("trace_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "tool_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("ai_run_id", sa.Uuid(), nullable=False),
        sa.Column("tool_name", sa.String(length=80), nullable=False),
        sa.Column("argument_hash", sa.String(length=64), nullable=False),
        sa.Column("result_hash", sa.String(length=64), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["ai_run_id"], ["ai_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("tool_executions")
    op.drop_table("ai_runs")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("export_jobs")
    op.drop_table("scenario_rules")
    op.drop_table("scenarios")
    op.drop_table("financial_entries")
    op.drop_table("import_errors")
    op.drop_table("import_jobs")
    op.drop_constraint("uq_cost_centers_org_id", "cost_centers", type_="unique")
    op.drop_constraint("uq_departments_org_id", "departments", type_="unique")
    op.drop_constraint("uq_budget_versions_org_id", "budget_versions", type_="unique")
