from __future__ import annotations

from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from budgetlens.dev_identities import (
    ALPHA_ADMIN_ID,
    ALPHA_ANALYST_ID,
    ALPHA_ORG_ID,
    ALPHA_VIEWER_ID,
    BETA_ORG_ID,
    BOTH_USER_ID,
    OPERATOR_ID,
)

PREFIX = "/api/v1"
UNKNOWN_ORG = UUID("99999999-9999-4999-8999-999999999999")


def _headers(
    user_id: UUID,
    organization_id: UUID | None = None,
) -> dict[str, str]:
    headers = {"Authorization": f"Bearer {user_id}"}
    if organization_id is not None:
        headers["X-Organization-Id"] = str(organization_id)
    return headers


def test_me_capabilities_follow_persona_matrix(seeded_client: TestClient) -> None:
    owner = seeded_client.get(
        f"{PREFIX}/me",
        headers=_headers(ALPHA_VIEWER_ID, ALPHA_ORG_ID),
    ).json()
    analyst = seeded_client.get(
        f"{PREFIX}/me",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    ).json()
    admin = seeded_client.get(
        f"{PREFIX}/me",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    ).json()
    operator = seeded_client.get(f"{PREFIX}/me", headers=_headers(OPERATOR_ID)).json()

    assert owner["persona"] == "budget_owner"
    assert owner["role"] == "viewer"
    assert owner["capabilities"]["can_view_dashboard"] is True
    assert owner["capabilities"]["can_use_copilot"] is True
    assert owner["capabilities"]["can_import"] is False
    assert owner["capabilities"]["can_create_scenario"] is False
    assert owner["capabilities"]["can_manage_members"] is False

    assert analyst["persona"] == "fpna_analyst"
    assert analyst["capabilities"]["can_import"] is True
    assert analyst["capabilities"]["can_publish_budget"] is True
    assert analyst["capabilities"]["can_create_scenario"] is True
    assert analyst["capabilities"]["can_manage_members"] is False

    assert admin["persona"] == "organization_admin"
    assert admin["capabilities"]["can_manage_members"] is True
    assert admin["capabilities"]["can_view_technical_metrics"] is False

    assert operator["persona"] == "platform_operator"
    assert operator["role"] is None
    assert operator["capabilities"]["can_view_dashboard"] is False
    assert operator["capabilities"]["can_use_copilot"] is False
    assert operator["capabilities"]["can_view_technical_metrics"] is True
    assert operator["capabilities"]["can_deploy_rollback"] is True


def test_operator_cannot_read_financial_data_or_create_org(seeded_client: TestClient) -> None:
    accounts = seeded_client.get(
        f"{PREFIX}/accounts",
        headers=_headers(OPERATOR_ID, ALPHA_ORG_ID),
    )
    assert accounts.status_code == 403
    assert "perteneces" not in accounts.json()["error"]["message"].lower()
    created = seeded_client.post(
        f"{PREFIX}/organizations",
        headers=_headers(OPERATOR_ID),
        json={
            "name": "Gamma",
            "slug": "gamma-ops",
            "functional_currency": "MXN",
            "fiscal_year_start_month": 1,
        },
    )
    assert created.status_code == 403
    orgs = seeded_client.get(f"{PREFIX}/organizations", headers=_headers(OPERATOR_ID))
    assert orgs.status_code == 200
    assert orgs.json()["items"] == []


def test_switching_organization_does_not_leak_other_tenant(seeded_client: TestClient) -> None:
    alpha = seeded_client.get(
        f"{PREFIX}/accounts",
        headers=_headers(BOTH_USER_ID, ALPHA_ORG_ID),
    )
    beta = seeded_client.get(
        f"{PREFIX}/accounts",
        headers=_headers(BOTH_USER_ID, BETA_ORG_ID),
    )
    assert alpha.status_code == 200
    assert beta.status_code == 200
    alpha_ids = {item["id"] for item in alpha.json()["items"]}
    beta_ids = {item["id"] for item in beta.json()["items"]}
    assert alpha_ids.isdisjoint(beta_ids)

    alpha_me = seeded_client.get(
        f"{PREFIX}/me",
        headers=_headers(BOTH_USER_ID, ALPHA_ORG_ID),
    ).json()
    beta_me = seeded_client.get(
        f"{PREFIX}/me",
        headers=_headers(BOTH_USER_ID, BETA_ORG_ID),
    ).json()
    assert alpha_me["role"] == "analyst"
    assert beta_me["role"] == "viewer"
    assert alpha_me["capabilities"]["can_import"] is True
    assert beta_me["capabilities"]["can_import"] is False

    leaked = seeded_client.get(
        f"{PREFIX}/accounts/{next(iter(alpha_ids))}",
        headers=_headers(BOTH_USER_ID, BETA_ORG_ID),
    )
    assert leaked.status_code == 404


def test_forged_organization_id_does_not_reveal_existence(seeded_client: TestClient) -> None:
    header = seeded_client.get(
        f"{PREFIX}/accounts",
        headers=_headers(ALPHA_ADMIN_ID, BETA_ORG_ID),
    )
    assert header.status_code == 403
    assert "beta" not in header.json()["error"]["message"].lower()
    assert "perteneces" not in header.json()["error"]["message"].lower()

    unknown = seeded_client.get(
        f"{PREFIX}/accounts",
        headers=_headers(ALPHA_ADMIN_ID, UNKNOWN_ORG),
    )
    assert unknown.status_code in {403, 404}
    assert "existen" not in unknown.json()["error"]["message"].lower()

    path = seeded_client.get(
        f"{PREFIX}/organizations/{BETA_ORG_ID}",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    )
    assert path.status_code in {403, 404}

    payload = seeded_client.patch(
        f"{PREFIX}/organizations/{BETA_ORG_ID}",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        json={"version": 1, "name": "Intruso"},
    )
    assert payload.status_code in {403, 404}

    random_account = seeded_client.get(
        f"{PREFIX}/accounts/{uuid4()}",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    )
    assert random_account.status_code == 404
