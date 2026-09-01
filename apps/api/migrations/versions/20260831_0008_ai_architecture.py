"""Add conversation retention and grounding_failed AI run status.

Revision ID: 20260831_0008
Revises: 20260831_0007
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0008"
down_revision: str | None = "20260831_0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "conversation_retention_days",
            sa.Integer(),
            nullable=False,
            server_default="90",
        ),
    )
    op.create_check_constraint(
        "ck_organizations_conversation_retention_days",
        "organizations",
        "conversation_retention_days BETWEEN 7 AND 365",
    )
    op.drop_constraint("ck_ai_runs_status", "ai_runs", type_="check")
    op.create_check_constraint(
        "ck_ai_runs_status",
        "ai_runs",
        "status IN ('succeeded', 'failed', 'limited', 'grounding_failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_ai_runs_status", "ai_runs", type_="check")
    op.create_check_constraint(
        "ck_ai_runs_status",
        "ai_runs",
        "status IN ('succeeded', 'failed', 'limited')",
    )
    op.drop_constraint(
        "ck_organizations_conversation_retention_days",
        "organizations",
        type_="check",
    )
    op.drop_column("organizations", "conversation_retention_days")
