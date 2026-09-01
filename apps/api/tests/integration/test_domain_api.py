from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from budgetlens.dev_identities import (
    ALPHA_ADMIN_ID,
    ALPHA_ANALYST_ID,
    ALPHA_ORG_ID,
    ALPHA_VIEWER_ID,
    BETA_ADMIN_ID,
    BETA_ORG_ID,
)
from budgetlens.seed import run_seed

PREFIX = "/api/v1"


def _headers(
    user_id: UUID,
    organization_id: UUID | None = None,
    idempotency: str | None = None,
) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {user_id}"}
    if organization_id is not None:
        headers["X-Organization-Id"] = str(organization_id)
    if idempotency is not None:
        headers["Idempotency-Key"] = idempotency
    return headers


@pytest.mark.integration
def test_seed_is_idempotent_and_isolates_tenants(seeded_client: TestClient) -> None:
    run_seed(include_financials=True)
    run_seed(include_financials=True)
    alpha = seeded_client.get(f"{PREFIX}/accounts", headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID))
    beta = seeded_client.get(f"{PREFIX}/accounts", headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID))
    assert alpha.status_code == 200
    assert beta.status_code == 200
    alpha_codes = {item["code"] for item in alpha.json()["items"]}
    beta_codes = {item["code"] for item in beta.json()["items"]}
    assert "4000" in alpha_codes
    assert "4000" in beta_codes
    assert "UNASSIGNED" in {
        item["code"]
        for item in seeded_client.get(
            f"{PREFIX}/cost-centers", headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID)
        ).json()["items"]
    }
    organizations = seeded_client.get(f"{PREFIX}/organizations", headers=_headers(ALPHA_ADMIN_ID))
    slugs = {item["slug"] for item in organizations.json()["items"]}
    assert slugs == {"alpha"}


@pytest.mark.integration
def test_viewer_cannot_create_and_analyst_can_manage_versions(seeded_client: TestClient) -> None:
    denied = seeded_client.post(
        f"{PREFIX}/accounts",
        headers=_headers(ALPHA_VIEWER_ID, ALPHA_ORG_ID),
        json={"code": "7000", "name": "Otros", "account_type": "expense"},
    )
    assert denied.status_code == 403
    created = seeded_client.post(
        f"{PREFIX}/budget-versions",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"name": "Plan 2026", "fiscal_year": 2026},
    )
    assert created.status_code == 201
    version_id = created.json()["id"]
    published = seeded_client.post(
        f"{PREFIX}/budget-versions/{version_id}/publish",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "publish-1"),
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    patched = seeded_client.patch(
        f"{PREFIX}/budget-versions/{version_id}",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"version": published.json()["version"], "name": "No se puede"},
    )
    assert patched.status_code == 409
    assert patched.json()["error"]["code"] == "VERSION_NOT_DRAFT"


@pytest.mark.integration
def test_admin_manages_members_and_viewer_cannot(seeded_client: TestClient) -> None:
    forbidden = seeded_client.post(
        f"{PREFIX}/memberships",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"user_id": str(BETA_ADMIN_ID), "role": "viewer"},
    )
    assert forbidden.status_code == 403
    created = seeded_client.post(
        f"{PREFIX}/memberships",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        json={"user_id": str(BETA_ADMIN_ID), "role": "viewer"},
    )
    assert created.status_code == 201


@pytest.mark.integration
def test_alpha_cannot_read_or_mutate_beta(seeded_client: TestClient) -> None:
    beta_account = seeded_client.get(
        f"{PREFIX}/accounts", headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID)
    ).json()["items"][0]
    cross_read = seeded_client.get(
        f"{PREFIX}/accounts/{beta_account['id']}",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    )
    assert cross_read.status_code == 404
    wrong_header = seeded_client.get(
        f"{PREFIX}/accounts",
        headers=_headers(ALPHA_ADMIN_ID, BETA_ORG_ID),
    )
    assert wrong_header.status_code == 403
    mutate = seeded_client.patch(
        f"{PREFIX}/accounts/{beta_account['id']}",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        json={"name": "Intruso"},
    )
    assert mutate.status_code == 404
    unchanged = seeded_client.get(
        f"{PREFIX}/accounts/{beta_account['id']}",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
    )
    assert unchanged.json()["name"] == beta_account["name"]


@pytest.mark.integration
def test_only_one_active_version_per_fiscal_year(seeded_client: TestClient) -> None:
    first = seeded_client.post(
        f"{PREFIX}/budget-versions",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        json={"name": "Activa A", "fiscal_year": 2027},
    ).json()
    second = seeded_client.post(
        f"{PREFIX}/budget-versions",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        json={"name": "Activa B", "fiscal_year": 2027},
    ).json()
    seeded_client.post(
        f"{PREFIX}/budget-versions/{first['id']}/publish",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID, "pub-a"),
    )
    seeded_client.post(
        f"{PREFIX}/budget-versions/{second['id']}/publish",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID, "pub-b"),
    )
    activated = seeded_client.post(
        f"{PREFIX}/budget-versions/{first['id']}/activate",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID, "act-a"),
    )
    switched = seeded_client.post(
        f"{PREFIX}/budget-versions/{second['id']}/activate",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID, "act-b"),
    )
    assert activated.status_code == 200
    assert switched.status_code == 200
    listed = seeded_client.get(
        f"{PREFIX}/budget-versions",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        params={"fiscal_year": 2027},
    ).json()["items"]
    active = [item for item in listed if item["is_active"]]
    assert len(active) == 1
    assert active[0]["id"] == second["id"]


@pytest.mark.integration
def test_concurrent_activate_keeps_single_active(
    seeded_client: TestClient, migrated_database: str
) -> None:
    del seeded_client
    first_id = (
        TestClient(create_app_for(migrated_database))
        .post(
            f"{PREFIX}/budget-versions",
            headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
            json={"name": "Concurrente A", "fiscal_year": 2028},
        )
        .json()["id"]
    )
    second_id = (
        TestClient(create_app_for(migrated_database))
        .post(
            f"{PREFIX}/budget-versions",
            headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
            json={"name": "Concurrente B", "fiscal_year": 2028},
        )
        .json()["id"]
    )
    for version_id, key in ((first_id, "c-pub-a"), (second_id, "c-pub-b")):
        TestClient(create_app_for(migrated_database)).post(
            f"{PREFIX}/budget-versions/{version_id}/publish",
            headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID, key),
        )

    def activate(version_id: str) -> int:
        client = TestClient(create_app_for(migrated_database))
        response = client.post(
            f"{PREFIX}/budget-versions/{version_id}/activate",
            headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID, str(uuid4())),
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(activate, [first_id, second_id]))
    listed = (
        TestClient(create_app_for(migrated_database))
        .get(
            f"{PREFIX}/budget-versions",
            headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
            params={"fiscal_year": 2028},
        )
        .json()["items"]
    )
    active = [item for item in listed if item["is_active"]]
    assert statuses.count(200) >= 1
    assert len(active) == 1


@pytest.mark.integration
def test_critical_actions_audit_success_and_denied(seeded_client: TestClient) -> None:
    denied = seeded_client.post(
        f"{PREFIX}/accounts",
        headers=_headers(ALPHA_VIEWER_ID, ALPHA_ORG_ID),
        json={"code": "8800", "name": "Denegado", "account_type": "expense"},
    )
    assert denied.status_code == 403
    assert denied.json()["trace_id"]
    created = seeded_client.post(
        f"{PREFIX}/accounts",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        json={"code": "8801", "name": "Auditoría", "account_type": "expense"},
    )
    assert created.status_code == 201
    success_events = seeded_client.get(
        f"{PREFIX}/audit-events",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        params={"action": "dimension.created"},
    )
    assert success_events.status_code == 200
    items = success_events.json()["items"]
    assert items
    event = items[0]
    assert event["outcome"] == "success"
    assert event["schema_version"] == "1.0"
    assert event["actor"]["type"] == "user"
    assert event["resource"]["type"] == "account"
    assert event["action"] == "dimension.created"
    assert "amount" not in event["metadata"]
    denied_events = seeded_client.get(
        f"{PREFIX}/audit-events",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        params={"action": "security.access_denied"},
    )
    assert denied_events.status_code == 200
    denied_items = denied_events.json()["items"]
    assert denied_items
    assert denied_items[0]["outcome"] == "denied"
    assert denied_items[0]["trace_id"]


def create_app_for(_url: str):
    from budgetlens.presentation.app import create_app

    return create_app()
