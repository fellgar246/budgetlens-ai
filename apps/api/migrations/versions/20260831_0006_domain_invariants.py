"""Add domain invariant checks, same-org AI FKs, and append-only audit.

Revision ID: 20260831_0006
Revises: 20260831_0005
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260831_0006"
down_revision: str | None = "20260831_0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_check_constraint("ck_users_status", "users", "status IN ('active', 'disabled')")
    op.create_check_constraint(
        "ck_memberships_role",
        "memberships",
        "role IN ('viewer', 'analyst', 'admin')",
    )
    op.create_check_constraint(
        "ck_memberships_status",
        "memberships",
        "status IN ('active', 'disabled')",
    )
    op.create_check_constraint(
        "ck_accounts_status",
        "accounts",
        "status IN ('active', 'inactive')",
    )
    op.create_check_constraint(
        "ck_accounts_type",
        "accounts",
        "account_type IN ('revenue', 'expense', 'asset', 'liability', 'equity', 'other')",
    )
    op.create_check_constraint(
        "ck_departments_status",
        "departments",
        "status IN ('active', 'inactive')",
    )
    op.create_check_constraint(
        "ck_cost_centers_status",
        "cost_centers",
        "status IN ('active', 'inactive')",
    )
    op.create_check_constraint("ck_import_jobs_sha256", "import_jobs", "char_length(sha256) = 64")
    op.create_check_constraint(
        "ck_import_errors_severity",
        "import_errors",
        "severity IN ('error', 'warning')",
    )
    op.create_check_constraint(
        "ck_financial_entries_period_start",
        "financial_entries",
        "EXTRACT(DAY FROM period_start) = 1",
    )
    op.create_check_constraint(
        "ck_financial_entries_currency",
        "financial_entries",
        "char_length(currency) = 3",
    )
    op.create_check_constraint(
        "ck_scenarios_baseline_type",
        "scenarios",
        "baseline_type IN ('budget', 'actual')",
    )
    op.create_check_constraint(
        "ck_scenarios_status",
        "scenarios",
        "status IN ('draft', 'saved', 'archived')",
    )
    op.create_check_constraint("ck_messages_role", "messages", "role IN ('user', 'assistant')")
    op.create_check_constraint(
        "ck_ai_runs_status",
        "ai_runs",
        "status IN ('succeeded', 'failed', 'limited')",
    )
    op.create_check_constraint(
        "ck_tool_executions_status",
        "tool_executions",
        "status IN ('succeeded', 'rejected', 'failed')",
    )

    op.create_unique_constraint("uq_ai_runs_org_id", "ai_runs", ["organization_id", "id"])
    op.drop_constraint("ai_runs_conversation_id_fkey", "ai_runs", type_="foreignkey")
    op.create_foreign_key(
        "fk_ai_runs_conversation_same_org",
        "ai_runs",
        "conversations",
        ["organization_id", "conversation_id"],
        ["organization_id", "id"],
    )
    op.drop_constraint("tool_executions_ai_run_id_fkey", "tool_executions", type_="foreignkey")
    op.create_foreign_key(
        "fk_tool_executions_run_same_org",
        "tool_executions",
        "ai_runs",
        ["organization_id", "ai_run_id"],
        ["organization_id", "id"],
    )

    op.execute(
        """
        CREATE FUNCTION audit_events_append_only() RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events is append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON audit_events
        FOR EACH ROW EXECUTE FUNCTION audit_events_append_only()
        """
    )


def downgrade() -> None:
    raise NotImplementedError("Forward-only migrations")
