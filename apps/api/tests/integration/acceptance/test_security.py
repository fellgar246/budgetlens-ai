# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false
from __future__ import annotations

import logging

import pytest
from fastapi.testclient import TestClient

from budgetlens.dev_identities import (
    ALPHA_ADMIN_ID,
    ALPHA_ANALYST_ID,
    ALPHA_ORG_ID,
    BETA_ADMIN_ID,
    BETA_ORG_ID,
    BOTH_USER_ID,
)
from budgetlens.logging import JsonLogFormatter
from tests.integration.acceptance.support import (
    PREFIX,
    auth_headers,
    create_budget_version,
    entry_count,
    import_workbook,
    sample_bytes,
    sensitive_leak,
)


def _beta_snapshot(client: TestClient) -> dict[str, dict[str, str] | list[str] | int]:
    accounts = client.get(f"{PREFIX}/accounts", headers=auth_headers(BETA_ADMIN_ID, BETA_ORG_ID))
    jobs = client.get(f"{PREFIX}/imports", headers=auth_headers(BETA_ADMIN_ID, BETA_ORG_ID))
    conversations = client.get(
        f"{PREFIX}/conversations", headers=auth_headers(BETA_ADMIN_ID, BETA_ORG_ID)
    )
    assert accounts.status_code == 200
    names = {str(item["id"]): str(item["name"]) for item in accounts.json()["items"]}
    return {
        "account_names": names,
        "job_ids": [str(item["id"]) for item in jobs.json()["items"]],
        "conversation_ids": [str(item["id"]) for item in conversations.json()["items"]],
        "entries": entry_count(organization_id=BETA_ORG_ID),
    }


def test_cross_tenant_read_is_denied_without_metadata(seeded_client: TestClient) -> None:
    beta_account = seeded_client.get(
        f"{PREFIX}/accounts", headers=auth_headers(BETA_ADMIN_ID, BETA_ORG_ID)
    ).json()["items"][0]
    cross = seeded_client.get(
        f"{PREFIX}/accounts/{beta_account['id']}",
        headers=auth_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    )
    assert cross.status_code in {403, 404}
    body = cross.json()
    assert "beta" not in str(body).lower()
    assert beta_account["name"].lower() not in str(body).lower()
    assert "error" in body
    assert set(body["error"]) <= {"code", "message", "field_errors", "retryable"}
    denied = seeded_client.get(
        f"{PREFIX}/accounts",
        headers=auth_headers(ALPHA_ADMIN_ID, BETA_ORG_ID),
    )
    assert denied.status_code in {403, 404}
    assert "beta" not in denied.json()["error"]["message"].lower()
    audits = seeded_client.get(
        f"{PREFIX}/audit-events",
        headers=auth_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        params={"action": "security.access_denied"},
    )
    assert audits.status_code == 200
    items = audits.json()["items"]
    assert items
    assert items[0]["outcome"] == "denied"
    assert not sensitive_leak(items[0]["metadata"])


def test_cross_tenant_mutations_leave_beta_unchanged(seeded_client: TestClient) -> None:
    before = _beta_snapshot(seeded_client)
    names = before["account_names"]
    assert isinstance(names, dict)
    beta_account_id = next(iter(names))
    beta_name = names[beta_account_id]
    version = seeded_client.post(
        f"{PREFIX}/budget-versions",
        headers=auth_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"name": "Beta acceptance", "fiscal_year": 2026},
    )
    assert version.status_code == 201
    version_id = version.json()["id"]
    content = (
        b"period,account_code,department_code,cost_center_code,amount,currency\n"
        b"2026-01,6100,OPS,CC-GEN,10.0000,USD\n"
    )
    job = import_workbook(
        seeded_client,
        content=content,
        filename="beta-accept.csv",
        import_type="budget",
        version_id=version_id,
        user=BETA_ADMIN_ID,
        org=BETA_ORG_ID,
        commit=False,
        idempotency="beta-ready",
    )
    conversation = seeded_client.post(
        f"{PREFIX}/conversations",
        headers=auth_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"title": "Beta chat", "context": {"budget_version_id": version_id}},
    )
    assert conversation.status_code == 201
    export = seeded_client.post(
        f"{PREFIX}/exports",
        headers=auth_headers(BETA_ADMIN_ID, BETA_ORG_ID),
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

    update = seeded_client.patch(
        f"{PREFIX}/accounts/{beta_account_id}",
        headers=auth_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        json={"name": "Intruso"},
    )
    assert update.status_code in {403, 404}
    commit = seeded_client.post(
        f"{PREFIX}/imports/{job['id']}/commit",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "ac012-commit"),
    )
    assert commit.status_code in {403, 404}
    export_cross = seeded_client.get(
        f"{PREFIX}/exports/{export.json()['id']}/content",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert export_cross.status_code in {403, 404}
    talk = seeded_client.post(
        f"{PREFIX}/conversations/{conversation.json()['id']}/messages",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"content": "Hola", "context": {"budget_version_id": version_id}},
    )
    assert talk.status_code in {403, 404}

    after = _beta_snapshot(seeded_client)
    unchanged = seeded_client.get(
        f"{PREFIX}/accounts/{beta_account_id}",
        headers=auth_headers(BETA_ADMIN_ID, BETA_ORG_ID),
    )
    assert unchanged.status_code == 200
    assert unchanged.json()["name"] == beta_name
    assert after["entries"] == before["entries"]
    beta_job = seeded_client.get(
        f"{PREFIX}/imports/{job['id']}",
        headers=auth_headers(BETA_ADMIN_ID, BETA_ORG_ID),
    )
    assert beta_job.status_code == 200
    assert beta_job.json()["status"] != "applied"


def test_switching_organization_uses_the_new_membership(seeded_client: TestClient) -> None:
    alpha = seeded_client.get(
        f"{PREFIX}/accounts",
        headers=auth_headers(BOTH_USER_ID, ALPHA_ORG_ID),
    )
    beta = seeded_client.get(
        f"{PREFIX}/accounts",
        headers=auth_headers(BOTH_USER_ID, BETA_ORG_ID),
    )
    assert alpha.status_code == 200
    assert beta.status_code == 200
    alpha_ids = {item["id"] for item in alpha.json()["items"]}
    beta_ids = {item["id"] for item in beta.json()["items"]}
    assert alpha_ids.isdisjoint(beta_ids)
    leaked = seeded_client.get(
        f"{PREFIX}/accounts/{next(iter(alpha_ids))}",
        headers=auth_headers(BOTH_USER_ID, BETA_ORG_ID),
    )
    assert leaked.status_code in {403, 404}
    me = seeded_client.get(f"{PREFIX}/me", headers=auth_headers(BOTH_USER_ID, BETA_ORG_ID))
    assert me.status_code == 200
    assert me.json()["role"] == "viewer"
    assert me.json()["capabilities"]["can_import"] is False


def test_formula_workbook_is_rejected_and_not_applied(seeded_client: TestClient) -> None:
    version_id = create_budget_version(seeded_client, "Acceptance formula")
    result = import_workbook(
        seeded_client,
        content=sample_bytes("formula.xlsx"),
        filename="formula.xlsx",
        import_type="budget",
        version_id=version_id,
        commit=False,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert result["status"] == "invalid"
    errors = seeded_client.get(
        f"{PREFIX}/imports/{result['id']}/errors",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    ).json()["items"]
    assert any(item["code"] == "FORMULA_NOT_ALLOWED" for item in errors)
    blocked = seeded_client.post(
        f"{PREFIX}/imports/{result['id']}/commit",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "ac014-blocked"),
    )
    assert blocked.status_code == 409
    assert entry_count(job_id=str(result["id"])) == 0
    assert "2.0000" not in str(errors)


def test_error_responses_and_logs_omit_secrets(
    seeded_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    token = "super-secret-token-ac016"
    database_url = "postgresql://budgetlens:budgetlens_local_only@localhost/budgetlens"
    caplog.set_level(logging.INFO)
    missing = seeded_client.get(
        f"{PREFIX}/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert missing.status_code == 401
    invalid = seeded_client.post(
        f"{PREFIX}/budget-versions",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"name": database_url, "fiscal_year": "not-a-year"},
    )
    rendered = missing.text + invalid.text
    assert token not in rendered
    assert "budgetlens_local_only" not in rendered
    formatter = JsonLogFormatter()
    logs = "\n".join(formatter.format(record) for record in caplog.records)
    assert token not in logs
    assert "budgetlens_local_only" not in logs
