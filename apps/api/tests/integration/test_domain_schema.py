from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, IntegrityError


@pytest.mark.integration
def test_schema_enforces_domain_invariants(migrated_database: str) -> None:
    engine = create_engine(migrated_database)
    inspector = inspect(engine)
    entry_indexes = {item["name"] for item in inspector.get_indexes("financial_entries")}
    budget_indexes = {item["name"] for item in inspector.get_indexes("budget_versions")}
    import_indexes = {item["name"] for item in inspector.get_indexes("import_jobs")}
    user_checks = {item["name"] for item in inspector.get_check_constraints("users")}
    membership_uniques = {item["name"] for item in inspector.get_unique_constraints("memberships")}
    assert "ix_financial_entries_org_fy_period" in entry_indexes
    assert "ix_financial_entries_org_fy_scenario_period" in entry_indexes
    assert "ix_financial_entries_org_version_period" in entry_indexes
    assert "ix_financial_entries_org_account_period" in entry_indexes
    assert "ix_financial_entries_org_department_period" in entry_indexes
    assert "ix_financial_entries_org_cost_center_period" in entry_indexes
    assert "ux_budget_versions_one_active" in budget_indexes
    assert "ux_import_jobs_fingerprint" in import_indexes
    assert "ck_users_status" in user_checks
    assert "uq_memberships_org_user" in membership_uniques

    now = "2026-01-01T00:00:00+00:00"
    user_id = str(uuid4())
    org_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, email, display_name, status, created_at, updated_at) "
                "VALUES (:id, 'ana@example.com', 'Ana', 'active', :now, :now)"
            ),
            {"id": user_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO organizations "
                "(id, name, slug, functional_currency, fiscal_year_start_month, "
                "status, created_at, updated_at, version) "
                "VALUES (:id, 'Org', 'alpha', 'MXN', 1, 'active', :now, :now, 1)"
            ),
            {"id": org_id, "now": now},
        )
        connection.execute(
            text(
                "INSERT INTO memberships "
                "(id, organization_id, user_id, role, status, created_at, updated_at) "
                "VALUES (:id, :org, :user_id, 'admin', 'active', :now, :now)"
            ),
            {"id": str(uuid4()), "org": org_id, "user_id": user_id, "now": now},
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE users SET status = 'unknown' WHERE id = :id"),
                {"id": user_id},
            )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO memberships "
                    "(id, organization_id, user_id, role, status, created_at, updated_at) "
                    "VALUES (:id, :org, :user_id, 'owner', 'active', :now, :now)"
                ),
                {"id": str(uuid4()), "org": org_id, "user_id": user_id, "now": now},
            )

    event_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO audit_events "
                "(id, organization_id, actor_id, action, resource_type, resource_id, "
                "outcome, metadata_json, trace_id, created_at, schema_version) "
                "VALUES (:id, :org, :actor, 'organization.create', 'organization', "
                ":org, 'success', '{}'::jsonb, 'trace', :now, 1)"
            ),
            {"id": event_id, "org": org_id, "actor": user_id, "now": now},
        )

    with pytest.raises(DBAPIError, match="append-only"):
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE audit_events SET outcome = 'denied' WHERE id = :id"),
                {"id": event_id},
            )

    with pytest.raises(DBAPIError, match="append-only"):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM audit_events WHERE id = :id"), {"id": event_id})

    engine.dispose()
