from __future__ import annotations

import hashlib
import io
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from budgetlens.dev_identities import (
    ALPHA_ADMIN_ID,
    ALPHA_ANALYST_ID,
    ALPHA_ORG_ID,
    ALPHA_VIEWER_ID,
    BETA_ADMIN_ID,
    BETA_ORG_ID,
)

PREFIX = "/api/v1"
ROOT = Path(__file__).resolve().parents[4]
SAMPLE = ROOT / "sample-data"
CANONICAL = {
    "period": "period",
    "account_code": "account_code",
    "department_code": "department_code",
    "cost_center_code": "cost_center_code",
    "amount": "amount",
    "currency": "currency",
}


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


def _read(name: str) -> bytes:
    return (SAMPLE / name).read_bytes()


def _create_version(client: TestClient, name: str = "Plan 2026") -> str:
    created = client.post(
        f"{PREFIX}/budget-versions",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"name": name, "fiscal_year": 2026},
    )
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _import_file(
    client: TestClient,
    *,
    content: bytes,
    filename: str,
    import_type: str,
    version_id: str | None,
    user: UUID = ALPHA_ANALYST_ID,
    org: UUID = ALPHA_ORG_ID,
    mapping: dict[str, str] | None = None,
    commit: bool = True,
    idempotency: str = "imp-1",
    media_type: str | None = None,
) -> dict[str, Any]:
    digest = hashlib.sha256(content).hexdigest()
    created = client.post(
        f"{PREFIX}/imports",
        headers=_headers(user, org),
        json={
            "import_type": import_type,
            "budget_version_id": version_id,
            "original_filename": filename,
            "size_bytes": len(content),
            "sha256": digest,
            "template_version": "1.0",
        },
    )
    assert created.status_code == 201, created.text
    job_id = created.json()["id"]
    uploaded = client.put(
        f"{PREFIX}/imports/{job_id}/content",
        headers={**_headers(user, org), "Content-Type": media_type or "text/csv"},
        content=content,
    )
    assert uploaded.status_code == 200, uploaded.text
    validated = client.post(
        f"{PREFIX}/imports/{job_id}/validate",
        headers=_headers(user, org),
        json={"mapping": mapping or CANONICAL, "create_missing_dimensions": False},
    )
    assert validated.status_code == 200, validated.text
    if not commit:
        return validated.json()
    committed = client.post(
        f"{PREFIX}/imports/{job_id}/commit",
        headers=_headers(user, org, idempotency),
    )
    return committed.json() | {"_status": committed.status_code, "_body": committed.json()}


@pytest.mark.integration
def test_valid_csv_and_xlsx_import_same_totals(seeded_client: TestClient) -> None:
    version_id = _create_version(seeded_client)
    csv_bytes = _read("budget-valid.csv")
    csv_job = _import_file(
        seeded_client,
        content=csv_bytes,
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="csv-budget",
    )
    assert csv_job["_status"] == 200
    assert csv_job["_body"]["status"] == "applied"
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    text = csv_bytes.decode("utf-8").strip().splitlines()
    for line in text:
        sheet.append(line.split(","))
    buffer = io.BytesIO()
    workbook.save(buffer)
    version_b = _create_version(seeded_client, "Plan 2026 B")
    xlsx_job = _import_file(
        seeded_client,
        content=buffer.getvalue(),
        filename="budget-valid.xlsx",
        import_type="budget",
        version_id=version_b,
        idempotency="xlsx-budget",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert xlsx_job["_status"] == 200
    assert xlsx_job["_body"]["valid_amount_total"] == csv_job["_body"]["valid_amount_total"]


@pytest.mark.integration
def test_invalid_row_blocks_commit_and_leaves_no_entries(seeded_client: TestClient) -> None:
    version_id = _create_version(seeded_client, "Invalid")
    result = _import_file(
        seeded_client,
        content=_read("invalid-row.csv"),
        filename="invalid-row.csv",
        import_type="budget",
        version_id=version_id,
        commit=False,
    )
    assert result["status"] == "invalid"
    assert result["error_count"] >= 1
    errors = seeded_client.get(
        f"{PREFIX}/imports/{result['id']}/errors",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert errors.status_code == 200
    assert any(item["code"] == "INVALID_AMOUNT" for item in errors.json()["items"])
    blocked = seeded_client.post(
        f"{PREFIX}/imports/{result['id']}/commit",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "blocked"),
    )
    assert blocked.status_code == 409


@pytest.mark.integration
def test_formula_xlsx_is_rejected(seeded_client: TestClient) -> None:
    version_id = _create_version(seeded_client, "Formula")
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(
        ["period", "account_code", "department_code", "cost_center_code", "amount", "currency"]
    )
    sheet.append(["2026-01", "6100", "OPS", "CC-GEN", "=1+1", "MXN"])
    buffer = io.BytesIO()
    workbook.save(buffer)
    result = _import_file(
        seeded_client,
        content=buffer.getvalue(),
        filename="formula.xlsx",
        import_type="budget",
        version_id=version_id,
        commit=False,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert result["status"] == "invalid"
    errors = seeded_client.get(
        f"{PREFIX}/imports/{result['id']}/errors",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    ).json()["items"]
    assert any(item["code"] == "FORMULA_NOT_ALLOWED" for item in errors)


@pytest.mark.integration
def test_commit_retry_is_idempotent_and_analytics_match(seeded_client: TestClient) -> None:
    version_id = _create_version(seeded_client, "Analytics")
    budget = _import_file(
        seeded_client,
        content=_read("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="budget-once",
    )
    assert budget["_status"] == 200
    retry = seeded_client.post(
        f"{PREFIX}/imports/{budget['_body']['id']}/commit",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "budget-once"),
    )
    assert retry.status_code == 200
    assert retry.json()["valid_count"] == budget["_body"]["valid_count"]
    seeded_client.post(
        f"{PREFIX}/budget-versions/{version_id}/publish",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "pub-an"),
    )
    actuals = _import_file(
        seeded_client,
        content=_read("actuals-valid.csv"),
        filename="actuals-valid.csv",
        import_type="actual",
        version_id=None,
        idempotency="actual-once",
    )
    assert actuals["_status"] == 200
    summary = seeded_client.get(
        f"{PREFIX}/analytics/variance-summary",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={
            "fiscal_year": 2026,
            "period_from": "2026-01-01",
            "period_to": "2026-01-01",
            "budget_version_id": version_id,
            "account_id": _account_id(seeded_client, "6110"),
        },
    )
    assert summary.status_code == 200, summary.text
    metrics = summary.json()["metrics"]
    assert metrics["budget_amount"] == "100000.0000"
    assert metrics["actual_amount"] == "130000.0000"
    assert metrics["variance_amount"] == "30000.0000"
    assert metrics["favorability"] == "unfavorable"
    zero = seeded_client.get(
        f"{PREFIX}/analytics/variance-summary",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={
            "fiscal_year": 2026,
            "period_from": "2026-03-01",
            "period_to": "2026-03-01",
            "budget_version_id": version_id,
            "account_id": _account_id(seeded_client, "6300"),
        },
    ).json()["metrics"]
    assert zero["variance_percent"] is None
    assert zero["variance_state"] == "unbounded"
    revenue = seeded_client.get(
        f"{PREFIX}/analytics/variance-summary",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={
            "fiscal_year": 2026,
            "period_from": "2026-01-01",
            "period_to": "2026-01-01",
            "budget_version_id": version_id,
            "account_id": _account_id(seeded_client, "4100"),
        },
    ).json()["metrics"]
    assert revenue["favorability"] == "unfavorable"
    revenue_feb = seeded_client.get(
        f"{PREFIX}/analytics/variance-summary",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={
            "fiscal_year": 2026,
            "period_from": "2026-02-01",
            "period_to": "2026-02-01",
            "budget_version_id": version_id,
            "account_id": _account_id(seeded_client, "4100"),
        },
    ).json()["metrics"]
    assert revenue_feb["favorability"] == "favorable"
    breakdown = seeded_client.get(
        f"{PREFIX}/analytics/variance-breakdown",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={
            "fiscal_year": 2026,
            "period_from": "2026-01-01",
            "period_to": "2026-01-01",
            "budget_version_id": version_id,
            "group_by": "department",
        },
    )
    assert breakdown.status_code == 200
    total_var = sum(
        (Decimal(item["metrics"]["variance_amount"]) for item in breakdown.json()["items"]),
        Decimal("0"),
    )
    all_summary = seeded_client.get(
        f"{PREFIX}/analytics/variance-summary",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={
            "fiscal_year": 2026,
            "period_from": "2026-01-01",
            "period_to": "2026-01-01",
            "budget_version_id": version_id,
        },
    ).json()["metrics"]
    assert f"{total_var:.4f}" == all_summary["variance_amount"]


@pytest.mark.integration
def test_viewer_cannot_import_and_alpha_cannot_read_beta_job(seeded_client: TestClient) -> None:
    denied = seeded_client.post(
        f"{PREFIX}/imports",
        headers=_headers(ALPHA_VIEWER_ID, ALPHA_ORG_ID),
        json={
            "import_type": "actual",
            "original_filename": "a.csv",
            "size_bytes": 10,
            "sha256": "a" * 64,
        },
    )
    assert denied.status_code == 403
    beta_version = seeded_client.post(
        f"{PREFIX}/budget-versions",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"name": "Beta Plan", "fiscal_year": 2026},
    )
    assert beta_version.status_code == 201
    content = (
        b"period,account_code,department_code,cost_center_code,amount,currency\n"
        b"2026-01,6100,OPS,CC-GEN,10.0000,USD\n"
    )
    digest = hashlib.sha256(content).hexdigest()
    created = seeded_client.post(
        f"{PREFIX}/imports",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={
            "import_type": "budget",
            "budget_version_id": beta_version.json()["id"],
            "original_filename": "beta.csv",
            "size_bytes": len(content),
            "sha256": digest,
        },
    )
    assert created.status_code == 201
    cross = seeded_client.get(
        f"{PREFIX}/imports/{created.json()['id']}",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    )
    assert cross.status_code == 404


@pytest.mark.integration
def test_scenario_preview_does_not_mutate_entries(seeded_client: TestClient) -> None:
    version_id = _create_version(seeded_client, "Scenario")
    _import_file(
        seeded_client,
        content=_read("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="scen-budget",
    )
    seeded_client.post(
        f"{PREFIX}/budget-versions/{version_id}/publish",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "pub-sc"),
    )
    preview = seeded_client.post(
        f"{PREFIX}/scenarios/preview",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            "fiscal_year": 2026,
            "period_from": "2026-01-01",
            "period_to": "2026-03-01",
            "budget_version_id": version_id,
            "baseline_type": "budget",
            "rules": [
                {
                    "sequence": 1,
                    "operation": "percentage_change",
                    "value": "0.0500",
                    "scope": {
                        "period_from": "2026-01-01",
                        "period_to": "2026-03-01",
                        "account_ids": [],
                        "department_ids": [],
                        "cost_center_ids": [],
                    },
                }
            ],
        },
    )
    assert preview.status_code == 200, preview.text
    original = seeded_client.get(
        f"{PREFIX}/analytics/variance-summary",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={
            "fiscal_year": 2026,
            "period_from": "2026-01-01",
            "period_to": "2026-03-01",
            "budget_version_id": version_id,
        },
    ).json()["metrics"]["budget_amount"]
    assert preview.json()["baseline"] == original
    assert preview.json()["result"] != original


@pytest.mark.integration
def test_copilot_uses_tools_and_rejects_mutations(seeded_client: TestClient) -> None:
    version_id = _create_version(seeded_client, "Copilot")
    _import_file(
        seeded_client,
        content=_read("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="ai-budget",
    )
    seeded_client.post(
        f"{PREFIX}/budget-versions/{version_id}/publish",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "pub-ai"),
    )
    _import_file(
        seeded_client,
        content=_read("actuals-valid.csv"),
        filename="actuals-valid.csv",
        import_type="actual",
        version_id=None,
        idempotency="ai-actual",
    )
    created = seeded_client.post(
        f"{PREFIX}/conversations",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            "title": "Consulta",
            "context": {
                "fiscal_year": 2026,
                "period_from": "2026-01-01",
                "period_to": "2026-03-01",
                "budget_version_id": version_id,
                "currency": "MXN",
            },
        },
    )
    assert created.status_code == 201
    conversation_id = created.json()["id"]
    asked = seeded_client.post(
        f"{PREFIX}/conversations/{conversation_id}/messages",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            "content": "¿Cuál fue la variación de Maintenance en enero?",
            "context": {
                "fiscal_year": 2026,
                "period_from": "2026-01-01",
                "period_to": "2026-03-01",
                "budget_version_id": version_id,
                "currency": "MXN",
            },
        },
    )
    assert asked.status_code == 200, asked.text
    assert asked.json()["evidence"]
    assert "30000" in asked.json()["answer"] or "30000.0000" in str(asked.json()["evidence"])
    mutation = seeded_client.post(
        f"{PREFIX}/conversations/{conversation_id}/messages",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            "content": "Cambia budget de Payroll a cero",
            "context": {
                "fiscal_year": 2026,
                "period_from": "2026-01-01",
                "period_to": "2026-03-01",
                "budget_version_id": version_id,
            },
        },
    )
    assert mutation.status_code == 200
    assert mutation.json()["evidence"] == []
    assert (
        "modificar" in mutation.json()["answer"].lower()
        or "no puedo" in mutation.json()["answer"].lower()
    )


def _account_id(client: TestClient, code: str) -> str:
    accounts = client.get(f"{PREFIX}/accounts", headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID))
    for item in accounts.json()["items"]:
        if item["code"] == code:
            return item["id"]
    raise AssertionError(code)
