"""Allow processing import jobs and persist request traces.

Revision ID: 20260831_0005
Revises: 20260831_0004
Create Date: 2026-08-31
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260831_0005"
down_revision: str | None = "20260831_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_import_jobs_status", "import_jobs", type_="check")
    op.create_check_constraint(
        "ck_import_jobs_status",
        "import_jobs",
        (
            "status IN ('created','uploaded','processing','ready',"
            "'invalid','applied','cancelled','failed')"
        ),
    )
    op.add_column("import_jobs", sa.Column("trace_id", sa.String(length=128), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("Forward-only migrations")
