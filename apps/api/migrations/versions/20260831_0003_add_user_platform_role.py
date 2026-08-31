"""Add optional platform role for operators.

Revision ID: 20260831_0003
Revises: 20260831_0002
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0003"
down_revision: str | None = "20260831_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("platform_role", sa.String(length=20), nullable=True))
    op.create_check_constraint(
        "ck_users_platform_role",
        "users",
        "platform_role IS NULL OR platform_role IN ('operator')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_platform_role", "users", type_="check")
    op.drop_column("users", "platform_role")
