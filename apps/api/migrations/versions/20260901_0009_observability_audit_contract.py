"""Add actor type/ref and audit outcome checks.

Revision ID: 20260901_0009
Revises: 20260831_0008
Create Date: 2026-09-01
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260901_0009"
down_revision: str | None = "20260831_0008"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "audit_events",
        sa.Column("actor_type", sa.String(length=16), nullable=False, server_default="user"),
    )
    op.add_column(
        "audit_events",
        sa.Column("actor_ref", sa.String(length=80), nullable=False, server_default=""),
    )
    op.alter_column(
        "audit_events",
        "actor_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_audit_events_actor_type",
        "audit_events",
        "actor_type IN ('user', 'system')",
    )
    op.create_check_constraint(
        "ck_audit_events_actor",
        "audit_events",
        "(actor_type = 'user' AND actor_id IS NOT NULL) OR actor_type = 'system'",
    )
    op.create_check_constraint(
        "ck_audit_events_outcome",
        "audit_events",
        "outcome IN ('success', 'denied', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_audit_events_outcome", "audit_events", type_="check")
    op.drop_constraint("ck_audit_events_actor", "audit_events", type_="check")
    op.drop_constraint("ck_audit_events_actor_type", "audit_events", type_="check")
    op.alter_column(
        "audit_events",
        "actor_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )
    op.drop_column("audit_events", "actor_ref")
    op.drop_column("audit_events", "actor_type")
