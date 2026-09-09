from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from budgetlens.dev_identities import (
    ALPHA_ADMIN_ID,
    ALPHA_ANALYST_ID,
    ALPHA_ORG_ID,
    ALPHA_VIEWER_ID,
    BETA_ADMIN_ID,
    BETA_ORG_ID,
)

PREFIX = "/api/v1"


def _headers(user_id: UUID, organization_id: UUID | None = None) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {user_id}"}
    if organization_id is not None:
        headers["X-Organization-Id"] = str(organization_id)
    return headers


@pytest.mark.integration
def test_runtime_role_has_no_bypass_and_rls_requires_org_guc(
    migrated_database: str,
    seeded_client: TestClient,
) -> None:
    del seeded_client
    engine = create_engine(migrated_database)
    try:
        with engine.connect() as connection:
            bypass = connection.execute(
                text("SELECT rolbypassrls FROM pg_roles WHERE rolname = 'budgetlens_app'")
            ).scalar_one()
            assert bypass is False
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL ROLE budgetlens_app"))
            hidden = connection.execute(text("SELECT count(*) FROM accounts")).scalar_one()
            assert hidden == 0
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL ROLE budgetlens_app"))
            connection.execute(
                text("SELECT set_config('app.organization_id', :org, true)"),
                {"org": str(ALPHA_ORG_ID)},
            )
            alpha = connection.execute(text("SELECT count(*) FROM accounts")).scalar_one()
            leaked = connection.execute(
                text("SELECT count(*) FROM accounts WHERE organization_id = :org"),
                {"org": str(BETA_ORG_ID)},
            ).scalar_one()
            assert alpha > 0
            assert leaked == 0
    finally:
        engine.dispose()


@pytest.mark.integration
def test_cross_tenant_idor_covers_jobs_scenarios_conversations_and_exports(
    seeded_client: TestClient,
) -> None:
    beta_version = seeded_client.post(
        f"{PREFIX}/budget-versions",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"name": "Beta IDOR", "fiscal_year": 2026},
    )
    assert beta_version.status_code == 201
    version_id = beta_version.json()["id"]
    content = (
        b"period,account_code,department_code,cost_center_code,amount,currency\n"
        b"2026-01,6100,OPS,CC-GEN,10.0000,USD\n"
    )
    created_job = seeded_client.post(
        f"{PREFIX}/imports",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={
            "import_type": "budget",
            "budget_version_id": version_id,
            "original_filename": "beta.csv",
            "size_bytes": len(content),
            "sha256": "a" * 64,
        },
    )
    assert created_job.status_code == 201
    job_id = created_job.json()["id"]

    scenario = seeded_client.post(
        f"{PREFIX}/scenarios",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={
            "name": "Beta escenario",
            "baseline_type": "budget",
            "budget_version_id": version_id,
            "fiscal_year": 2026,
            "rules": [],
        },
    )
    assert scenario.status_code == 201
    scenario_id = scenario.json()["id"]

    conversation = seeded_client.post(
        f"{PREFIX}/conversations",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"title": "Beta chat", "context": {}},
    )
    assert conversation.status_code == 201
    conversation_id = conversation.json()["id"]

    export = seeded_client.post(
        f"{PREFIX}/exports",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={
            "filters": {
                "fiscal_year": 2026,
                "period_from": "2026-01-01",
                "period_to": "2026-01-01",
                "budget_version_id": version_id,
            },
            "group_by": "account",
        },
    )
    assert export.status_code == 200, export.text
    export_id = export.json()["id"]

    for path in (
        f"{PREFIX}/imports/{job_id}",
        f"{PREFIX}/imports/{job_id}/errors",
        f"{PREFIX}/imports/{job_id}/preview",
        f"{PREFIX}/imports/{job_id}/error-report",
        f"{PREFIX}/scenarios/{scenario_id}",
        f"{PREFIX}/conversations/{conversation_id}",
        f"{PREFIX}/conversations/{conversation_id}/messages",
        f"{PREFIX}/exports/{export_id}/content",
    ):
        read = seeded_client.get(path, headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID))
        assert read.status_code in {403, 404}, path

    listed_jobs = seeded_client.get(
        f"{PREFIX}/imports",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    )
    assert listed_jobs.status_code == 200
    assert job_id not in {item["id"] for item in listed_jobs.json()["items"]}

    listed_scenarios = seeded_client.get(
        f"{PREFIX}/scenarios",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    )
    assert scenario_id not in {item["id"] for item in listed_scenarios.json()["items"]}

    listed_conversations = seeded_client.get(
        f"{PREFIX}/conversations",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    )
    assert conversation_id not in {item["id"] for item in listed_conversations.json()["items"]}

    mutate_scenario = seeded_client.patch(
        f"{PREFIX}/scenarios/{scenario_id}",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"name": "Intruso"},
    )
    assert mutate_scenario.status_code in {403, 404}

    mutate_conversation = seeded_client.delete(
        f"{PREFIX}/conversations/{conversation_id}",
        headers=_headers(ALPHA_VIEWER_ID, ALPHA_ORG_ID),
    )
    assert mutate_conversation.status_code in {403, 404}


@pytest.mark.integration
def test_analyst_dimension_management_is_limited(seeded_client: TestClient) -> None:
    created = seeded_client.post(
        f"{PREFIX}/departments",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"code": "LIM", "name": "Limitada"},
    )
    assert created.status_code == 201
    renamed = seeded_client.patch(
        f"{PREFIX}/departments/{created.json()['id']}",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"name": "Renombrada"},
    )
    assert renamed.status_code == 200
    deactivated = seeded_client.patch(
        f"{PREFIX}/departments/{created.json()['id']}",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"status": "inactive"},
    )
    assert deactivated.status_code == 403
    admin = seeded_client.patch(
        f"{PREFIX}/departments/{created.json()['id']}",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        json={"status": "inactive"},
    )
    assert admin.status_code == 200
