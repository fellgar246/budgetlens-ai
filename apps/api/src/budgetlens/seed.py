from __future__ import annotations

from sqlalchemy import text

from budgetlens.adapters.db import session_scope


def run_seed() -> None:
    with session_scope() as session:
        session.execute(
            text(
                """
                INSERT INTO schema_meta (key, value)
                VALUES ('demo_dataset', 'synthetic-local')
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = now()
                """
            )
        )
