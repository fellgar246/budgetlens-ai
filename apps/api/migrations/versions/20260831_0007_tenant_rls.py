"""Enable tenant RLS and a runtime role without BYPASSRLS.

Revision ID: 20260831_0007
Revises: 20260831_0006
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260831_0007"
down_revision: str | None = "20260831_0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

RUNTIME_ROLE = "budgetlens_app"

TENANT_TABLES = (
    "accounts",
    "departments",
    "cost_centers",
    "budget_versions",
    "idempotency_records",
    "import_jobs",
    "import_errors",
    "financial_entries",
    "scenarios",
    "scenario_rules",
    "export_jobs",
    "conversations",
    "messages",
    "ai_runs",
    "tool_executions",
)


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{RUNTIME_ROLE}') THEN
                CREATE ROLE {RUNTIME_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS;
            ELSE
                ALTER ROLE {RUNTIME_ROLE} NOBYPASSRLS;
            END IF;
        END
        $$
        """
    )
    op.execute(f"GRANT {RUNTIME_ROLE} TO CURRENT_USER")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_organization_id() RETURNS uuid
        LANGUAGE sql STABLE
        AS $$
            SELECT NULLIF(current_setting('app.organization_id', true), '')::uuid
        $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app_current_user_id() RETURNS uuid
        LANGUAGE sql STABLE
        AS $$
            SELECT NULLIF(current_setting('app.user_id', true), '')::uuid
        $$
        """
    )
    op.execute(f"GRANT USAGE ON SCHEMA public TO {RUNTIME_ROLE}")
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {RUNTIME_ROLE}"
    )
    op.execute(
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE "
        f"ON TABLES TO {RUNTIME_ROLE}"
    )

    org_predicate = "organization_id = app_current_organization_id()"
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            FOR ALL TO {RUNTIME_ROLE}
            USING ({org_predicate})
            WITH CHECK ({org_predicate})
            """
        )

    op.execute("ALTER TABLE memberships ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE memberships FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_or_own_membership ON memberships
        FOR ALL TO {RUNTIME_ROLE}
        USING (
            organization_id = app_current_organization_id()
            OR user_id = app_current_user_id()
        )
        WITH CHECK (organization_id = app_current_organization_id())
        """
    )

    op.execute("ALTER TABLE organizations ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE organizations FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY organizations_select ON organizations
        FOR SELECT TO {RUNTIME_ROLE}
        USING (
            id = app_current_organization_id()
            OR EXISTS (
                SELECT 1 FROM memberships m
                WHERE m.organization_id = organizations.id
                  AND m.user_id = app_current_user_id()
            )
        )
        """
    )
    op.execute(
        f"""
        CREATE POLICY organizations_insert ON organizations
        FOR INSERT TO {RUNTIME_ROLE}
        WITH CHECK (app_current_user_id() IS NOT NULL)
        """
    )
    op.execute(
        f"""
        CREATE POLICY organizations_update ON organizations
        FOR UPDATE TO {RUNTIME_ROLE}
        USING (id = app_current_organization_id())
        WITH CHECK (id = app_current_organization_id())
        """
    )

    op.execute("ALTER TABLE audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_events FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY audit_tenant_or_unscoped ON audit_events
        FOR ALL TO {RUNTIME_ROLE}
        USING (
            organization_id IS NULL
            OR organization_id = app_current_organization_id()
        )
        WITH CHECK (
            organization_id IS NULL
            OR organization_id = app_current_organization_id()
        )
        """
    )


def downgrade() -> None:
    raise NotImplementedError("Forward-only migrations")
