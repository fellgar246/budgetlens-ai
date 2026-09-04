"""Add the analytics read index used by tenant-scoped SUM queries.

Revision ID: 20260902_0010
Revises: 20260901_0009
Create Date: 2026-09-02
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "20260902_0010"
down_revision: str | None = "20260901_0009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_financial_entries_org_fy_scenario_period",
        "financial_entries",
        ["organization_id", "fiscal_year", "scenario_type", "period_start"],
    )


def downgrade() -> None:
    raise NotImplementedError("Forward-only migrations")
