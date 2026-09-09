"""Separate the migration role from the runtime role.

Revision ID: 20260903_0011
Revises: 20260902_0010
Create Date: 2026-09-03
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260903_0011"
down_revision: str | None = "20260902_0010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

RUNTIME_ROLE = "budgetlens_app"
MIGRATOR_ROLE = "budgetlens_migrator"


def upgrade() -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{MIGRATOR_ROLE}') THEN
                CREATE ROLE {MIGRATOR_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS;
            ELSE
                ALTER ROLE {MIGRATOR_ROLE} NOBYPASSRLS;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{RUNTIME_ROLE}') THEN
                CREATE ROLE {RUNTIME_ROLE} NOLOGIN NOSUPERUSER NOBYPASSRLS;
            ELSE
                ALTER ROLE {RUNTIME_ROLE} NOBYPASSRLS;
            END IF;
        END
        $$
        """
    )
    op.execute(f"GRANT {MIGRATOR_ROLE} TO CURRENT_USER")
    op.execute(f"GRANT {RUNTIME_ROLE} TO CURRENT_USER")


def downgrade() -> None:
    raise NotImplementedError("Forward-only migrations")
