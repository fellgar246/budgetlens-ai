from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from budgetlens.dev_identities import (
    ALPHA_ADMIN_ID,
    ALPHA_ORG_ID,
    ALPHA_VIEWER_ID,
    BETA_ADMIN_ID,
    BETA_ORG_ID,
)

PREFIX = "/api/v1"


def _headers(
    user_id: UUID,
    organization_id: UUID | None = None,
    *,
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {user_id}"}
    if organization_id is not None:
        headers["X-Organization-Id"] = str(organization_id)
    if extra:
        headers.update(extra)
    return headers


def _create_beta_fixture(client: TestClient) -> dict[str, str]:
    version = client.post(
        f"{PREFIX}/budget-versions",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"name": "Beta matrix", "fiscal_year": 2026},
    )
    assert version.status_code == 201, version.text
    version_id = version.json()["id"]
    content = (
        b"period,account_code,department_code,cost_center_code,amount,currency\n"
        b"2026-01,6100,OPS,CC-GEN,10.0000,USD\n"
    )
    created_job = client.post(
        f"{PREFIX}/imports",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={
            "import_type": "budget",
            "budget_version_id": version_id,
            "original_filename": "beta-matrix.csv",
            "size_bytes": len(content),
            "sha256": "b" * 64,
        },
    )
    assert created_job.status_code == 201, created_job.text
    job_id = created_job.json()["id"]
    scenario = client.post(
        f"{PREFIX}/scenarios",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={
            "name": "Beta matrix scenario",
            "baseline_type": "budget",
            "budget_version_id": version_id,
            "fiscal_year": 2026,
            "rules": [],
        },
    )
    assert scenario.status_code == 201, scenario.text
    conversation = client.post(
        f"{PREFIX}/conversations",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"title": "Beta matrix chat", "context": {}},
    )
    assert conversation.status_code == 201, conversation.text
    export = client.post(
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
    account = client.post(
        f"{PREFIX}/accounts",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"code": "MX-ACC", "name": "Matrix account", "account_type": "expense"},
    )
    assert account.status_code == 201, account.text
    department = client.post(
        f"{PREFIX}/departments",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"code": "MX-DEP", "name": "Matrix department"},
    )
    assert department.status_code == 201, department.text
    cost_center = client.post(
        f"{PREFIX}/cost-centers",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"code": "MX-CC", "name": "Matrix cost center"},
    )
    assert cost_center.status_code == 201, cost_center.text
    memberships = client.get(
        f"{PREFIX}/memberships",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
    )
    assert memberships.status_code == 200
    membership_id = memberships.json()["items"][0]["id"]
    return {
        "version_id": version_id,
        "job_id": job_id,
        "scenario_id": scenario.json()["id"],
        "conversation_id": conversation.json()["id"],
        "export_id": export.json()["id"],
        "account_id": account.json()["id"],
        "department_id": department.json()["id"],
        "cost_center_id": cost_center.json()["id"],
        "membership_id": membership_id,
        "organization_id": str(BETA_ORG_ID),
    }


def _matrix_cases(
    ids: dict[str, str],
) -> list[tuple[str, str, dict[str, Any] | None, dict[str, str]]]:
    query = (
        f"fiscal_year=2026&period_from=2026-01-01&period_to=2026-01-01"
        f"&budget_version_id={ids['version_id']}"
    )
    idempotent = {"Idempotency-Key": str(uuid4())}
    return [
        ("GET", f"{PREFIX}/accounts/{ids['account_id']}", None, {}),
        ("PATCH", f"{PREFIX}/accounts/{ids['account_id']}", {"name": "Intruso"}, {}),
        ("GET", f"{PREFIX}/departments/{ids['department_id']}", None, {}),
        ("PATCH", f"{PREFIX}/departments/{ids['department_id']}", {"name": "Intruso"}, {}),
        ("GET", f"{PREFIX}/cost-centers/{ids['cost_center_id']}", None, {}),
        ("PATCH", f"{PREFIX}/cost-centers/{ids['cost_center_id']}", {"name": "Intruso"}, {}),
        ("GET", f"{PREFIX}/budget-versions/{ids['version_id']}", None, {}),
        (
            "PATCH",
            f"{PREFIX}/budget-versions/{ids['version_id']}",
            {"name": "Intruso", "version": 1},
            {},
        ),
        ("POST", f"{PREFIX}/budget-versions/{ids['version_id']}/publish", {}, idempotent),
        ("POST", f"{PREFIX}/budget-versions/{ids['version_id']}/activate", {}, idempotent),
        ("POST", f"{PREFIX}/budget-versions/{ids['version_id']}/archive", {}, idempotent),
        ("GET", f"{PREFIX}/imports/{ids['job_id']}", None, {}),
        ("GET", f"{PREFIX}/imports/{ids['job_id']}/errors", None, {}),
        ("GET", f"{PREFIX}/imports/{ids['job_id']}/preview", None, {}),
        ("GET", f"{PREFIX}/imports/{ids['job_id']}/error-report", None, {}),
        (
            "POST",
            f"{PREFIX}/imports/{ids['job_id']}/validate",
            {
                "mapping": {"period": "period", "amount": "amount"},
                "create_missing_dimensions": False,
            },
            {},
        ),
        ("POST", f"{PREFIX}/imports/{ids['job_id']}/cancel", {}, {}),
        ("GET", f"{PREFIX}/scenarios/{ids['scenario_id']}", None, {}),
        ("PATCH", f"{PREFIX}/scenarios/{ids['scenario_id']}", {"name": "Intruso"}, {}),
        ("POST", f"{PREFIX}/scenarios/{ids['scenario_id']}/archive", {}, {}),
        ("GET", f"{PREFIX}/conversations/{ids['conversation_id']}", None, {}),
        ("GET", f"{PREFIX}/conversations/{ids['conversation_id']}/messages", None, {}),
        (
            "POST",
            f"{PREFIX}/conversations/{ids['conversation_id']}/messages",
            {"content": "¿Cuál es el gasto de Beta?", "context": {}},
            {},
        ),
        ("DELETE", f"{PREFIX}/conversations/{ids['conversation_id']}", None, {}),
        ("GET", f"{PREFIX}/exports/{ids['export_id']}/content", None, {}),
        ("PATCH", f"{PREFIX}/memberships/{ids['membership_id']}", {"role": "viewer"}, {}),
        ("GET", f"{PREFIX}/organizations/{ids['organization_id']}", None, {}),
        (
            "PATCH",
            f"{PREFIX}/organizations/{ids['organization_id']}",
            {"name": "Intruso", "version": 1},
            {},
        ),
        ("GET", f"{PREFIX}/analytics/variance-summary?{query}", None, {}),
        ("GET", f"{PREFIX}/analytics/variance-breakdown?{query}&group_by=account", None, {}),
    ]


OMITTED_HEADER_PATHS = (
    f"{PREFIX}/accounts",
    f"{PREFIX}/departments",
    f"{PREFIX}/cost-centers",
    f"{PREFIX}/budget-versions",
    f"{PREFIX}/imports",
    f"{PREFIX}/scenarios",
    f"{PREFIX}/conversations",
    f"{PREFIX}/memberships",
    f"{PREFIX}/audit-events",
)


@pytest.mark.integration
def test_cross_tenant_matrix_denies_every_tenant_resource(seeded_client: TestClient) -> None:
    ids = _create_beta_fixture(seeded_client)
    beta_account = seeded_client.get(
        f"{PREFIX}/accounts/{ids['account_id']}",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
    )
    assert beta_account.status_code == 200
    original_name = beta_account.json()["name"]

    for method, path, body, extra in _matrix_cases(ids):
        headers = _headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID, extra=extra)
        response = seeded_client.request(method, path, headers=headers, json=body)
        assert response.status_code in {403, 404}, f"{method} {path} -> {response.status_code}"
        assert "Organización Beta" not in response.text

    still = seeded_client.get(
        f"{PREFIX}/accounts/{ids['account_id']}",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
    )
    assert still.status_code == 200
    assert still.json()["name"] == original_name

    listed = seeded_client.get(f"{PREFIX}/imports", headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID))
    assert listed.status_code == 200
    assert ids["job_id"] not in {item["id"] for item in listed.json()["items"]}


@pytest.mark.integration
def test_omitted_and_foreign_tenant_header_are_closed(seeded_client: TestClient) -> None:
    for path in OMITTED_HEADER_PATHS:
        omitted = seeded_client.get(path, headers=_headers(ALPHA_ADMIN_ID))
        assert omitted.status_code == 403, path
        forged = seeded_client.get(path, headers=_headers(ALPHA_ADMIN_ID, BETA_ORG_ID))
        assert forged.status_code == 403, path


@pytest.mark.integration
def test_disabled_user_and_membership_are_rejected(
    migrated_database: str, seeded_client: TestClient
) -> None:
    memberships = seeded_client.get(
        f"{PREFIX}/memberships",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    )
    assert memberships.status_code == 200
    viewer = next(
        item for item in memberships.json()["items"] if item["user_id"] == str(ALPHA_VIEWER_ID)
    )
    disabled = seeded_client.patch(
        f"{PREFIX}/memberships/{viewer['id']}",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        json={"status": "disabled"},
    )
    assert disabled.status_code == 200
    denied = seeded_client.get(
        f"{PREFIX}/accounts",
        headers=_headers(ALPHA_VIEWER_ID, ALPHA_ORG_ID),
    )
    assert denied.status_code == 403

    engine = create_engine(migrated_database)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("UPDATE users SET status = 'disabled' WHERE id = :id"),
                {"id": str(ALPHA_ADMIN_ID)},
            )
    finally:
        engine.dispose()
    unauthenticated = seeded_client.get(
        f"{PREFIX}/me",
        headers=_headers(ALPHA_ADMIN_ID),
    )
    assert unauthenticated.status_code == 401


@pytest.mark.integration
def test_migrator_and_runtime_roles_are_separated(
    migrated_database: str, seeded_client: TestClient
) -> None:
    del seeded_client
    engine = create_engine(migrated_database)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(
                    "SELECT rolname, rolbypassrls FROM pg_roles "
                    "WHERE rolname IN ('budgetlens_app', 'budgetlens_migrator')"
                )
            ).all()
            roles = {row[0]: row[1] for row in rows}
            assert set(roles) == {"budgetlens_app", "budgetlens_migrator"}
            assert roles["budgetlens_app"] is False
            assert roles["budgetlens_migrator"] is False
    finally:
        engine.dispose()
