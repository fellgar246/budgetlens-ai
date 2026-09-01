from __future__ import annotations

from decimal import Decimal

from fastapi.testclient import TestClient

from budgetlens.dev_identities import ALPHA_ANALYST_ID, ALPHA_ORG_ID
from tests.integration.acceptance.support import (
    PREFIX,
    account_id,
    auth_headers,
    create_account,
    create_budget_version,
    entry_count,
    import_workbook,
    sample_bytes,
    summary_metrics,
)


def _csv(rows: list[str]) -> bytes:
    header = "period,account_code,department_code,cost_center_code,amount,currency"
    return "\n".join([header, *rows, ""]).encode("utf-8")


def test_valid_import_applies_once_and_dashboard_matches(seeded_client: TestClient) -> None:
    version_id = create_budget_version(seeded_client, "Acceptance valid")
    job = import_workbook(
        seeded_client,
        content=sample_bytes("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="ac002-budget",
    )
    assert job["_status"] == 200
    body = job["_body"]
    assert body["status"] == "applied"
    assert body["valid_count"] >= 1
    assert entry_count(job_id=str(body["id"])) == body["valid_count"]
    first = summary_metrics(
        seeded_client,
        version_id=version_id,
        period_from="2026-01-01",
        period_to="2026-03-01",
    )
    assert first["budget_amount"] == body["valid_amount_total"]
    second = summary_metrics(
        seeded_client,
        version_id=version_id,
        period_from="2026-01-01",
        period_to="2026-03-01",
    )
    assert second == first
    replay = import_workbook(
        seeded_client,
        content=sample_bytes("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        commit=False,
        idempotency="ac002-replay",
    )
    assert replay["id"] == body["id"]
    assert replay["status"] == "applied"
    assert entry_count(job_id=str(body["id"])) == body["valid_count"]


def test_invalid_row_blocks_commit_and_leaves_no_entries(seeded_client: TestClient) -> None:
    version_id = create_budget_version(seeded_client, "Acceptance invalid")
    result = import_workbook(
        seeded_client,
        content=sample_bytes("invalid-row.csv"),
        filename="invalid-row.csv",
        import_type="budget",
        version_id=version_id,
        commit=False,
    )
    assert result["status"] == "invalid"
    errors = seeded_client.get(
        f"{PREFIX}/imports/{result['id']}/errors",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert errors.status_code == 200
    items = errors.json()["items"]
    assert items
    assert all("row_number" in item and "code" in item for item in items)
    blocked = seeded_client.post(
        f"{PREFIX}/imports/{result['id']}/commit",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "ac003-blocked"),
    )
    assert blocked.status_code == 409
    assert entry_count(job_id=str(result["id"])) == 0


def test_commit_retry_keeps_the_same_row_count(seeded_client: TestClient) -> None:
    version_id = create_budget_version(seeded_client, "Acceptance retry")
    first = import_workbook(
        seeded_client,
        content=sample_bytes("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="ac004-once",
    )
    assert first["_status"] == 200
    rows_before = entry_count(job_id=str(first["_body"]["id"]))
    retry = seeded_client.post(
        f"{PREFIX}/imports/{first['_body']['id']}/commit",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "ac004-once"),
    )
    assert retry.status_code == 200
    assert retry.json()["id"] == first["_body"]["id"]
    assert retry.json()["valid_count"] == first["_body"]["valid_count"]
    assert retry.json()["valid_amount_total"] == first["_body"]["valid_amount_total"]
    assert entry_count(job_id=str(first["_body"]["id"])) == rows_before


def test_zero_budget_is_unbounded_with_null_percent(seeded_client: TestClient) -> None:
    create_account(seeded_client, code="7112", name="Zero budget", account_type="expense")
    version_id = create_budget_version(seeded_client, "Acceptance zero")
    budget = import_workbook(
        seeded_client,
        content=_csv(["2026-01,7112,OPS,CC-GEN,0.0000,MXN"]),
        filename="zero-budget.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="ac005-budget",
    )
    assert budget["_status"] == 200
    actual = import_workbook(
        seeded_client,
        content=_csv(["2026-01,7112,OPS,CC-GEN,25.0000,MXN"]),
        filename="zero-actual.csv",
        import_type="actual",
        version_id=None,
        idempotency="ac005-actual",
    )
    assert actual["_status"] == 200
    metrics = summary_metrics(
        seeded_client,
        version_id=version_id,
        account=account_id(seeded_client, "7112"),
    )
    assert metrics["variance_amount"] == "25.0000"
    assert metrics["variance_percent"] is None
    assert metrics["variance_state"] == "unbounded"


def test_expense_over_budget_is_unfavorable(seeded_client: TestClient) -> None:
    create_account(seeded_client, code="7110", name="Catalog expense", account_type="expense")
    version_id = create_budget_version(seeded_client, "Acceptance expense")
    assert (
        import_workbook(
            seeded_client,
            content=_csv(["2026-01,7110,OPS,CC-GEN,100.0000,MXN"]),
            filename="expense-budget.csv",
            import_type="budget",
            version_id=version_id,
            idempotency="ac006-budget",
        )["_status"]
        == 200
    )
    assert (
        import_workbook(
            seeded_client,
            content=_csv(["2026-01,7110,OPS,CC-GEN,120.0000,MXN"]),
            filename="expense-actual.csv",
            import_type="actual",
            version_id=None,
            idempotency="ac006-actual",
        )["_status"]
        == 200
    )
    metrics = summary_metrics(
        seeded_client,
        version_id=version_id,
        account=account_id(seeded_client, "7110"),
    )
    assert metrics["variance_amount"] == "20.0000"
    assert metrics["favorability"] == "unfavorable"


def test_revenue_over_budget_is_favorable(seeded_client: TestClient) -> None:
    create_account(seeded_client, code="4111", name="Catalog revenue", account_type="revenue")
    version_id = create_budget_version(seeded_client, "Acceptance revenue")
    assert (
        import_workbook(
            seeded_client,
            content=_csv(["2026-01,4111,SALES,CC-GEN,100.0000,MXN"]),
            filename="revenue-budget.csv",
            import_type="budget",
            version_id=version_id,
            idempotency="ac007-budget",
        )["_status"]
        == 200
    )
    assert (
        import_workbook(
            seeded_client,
            content=_csv(["2026-01,4111,SALES,CC-GEN,120.0000,MXN"]),
            filename="revenue-actual.csv",
            import_type="actual",
            version_id=None,
            idempotency="ac007-actual",
        )["_status"]
        == 200
    )
    metrics = summary_metrics(
        seeded_client,
        version_id=version_id,
        account=account_id(seeded_client, "4111"),
    )
    assert metrics["variance_amount"] == "20.0000"
    assert metrics["favorability"] == "favorable"


def test_department_breakdown_sums_to_filtered_total(seeded_client: TestClient) -> None:
    version_id = create_budget_version(seeded_client, "Acceptance drill")
    import_workbook(
        seeded_client,
        content=sample_bytes("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="ac008-budget",
    )
    import_workbook(
        seeded_client,
        content=sample_bytes("actuals-valid.csv"),
        filename="actuals-valid.csv",
        import_type="actual",
        version_id=None,
        idempotency="ac008-actual",
    )
    params = {
        "fiscal_year": 2026,
        "period_from": "2026-01-01",
        "period_to": "2026-01-01",
        "budget_version_id": version_id,
    }
    total = seeded_client.get(
        f"{PREFIX}/analytics/variance-summary",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params=params,
    )
    assert total.status_code == 200, total.text
    breakdown = seeded_client.get(
        f"{PREFIX}/analytics/variance-breakdown",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={**params, "group_by": "department"},
    )
    assert breakdown.status_code == 200, breakdown.text
    parts = sum(
        (Decimal(item["metrics"]["variance_amount"]) for item in breakdown.json()["items"]),
        Decimal("0"),
    )
    assert f"{parts:.4f}" == total.json()["metrics"]["variance_amount"]
    href = (
        "/variances?version="
        f"{version_id}&period_from=2026-01-01&period_to=2026-01-01&department=ops"
    )
    assert "version=" in href and "department=ops" in href


def test_export_csv_matches_scope_currency_version_and_totals(
    seeded_client: TestClient,
) -> None:
    version_id = create_budget_version(seeded_client, "Acceptance export")
    import_workbook(
        seeded_client,
        content=sample_bytes("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="ac009-budget",
    )
    created = seeded_client.post(
        f"{PREFIX}/exports",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
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
    assert created.status_code == 200, created.text
    content = seeded_client.get(
        f"{PREFIX}/exports/{created.json()['id']}/content",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert content.status_code == 200, content.text
    text = content.text.lstrip("\ufeff")
    rows = [line for line in text.splitlines() if line]
    assert rows[0].startswith("organization_id,currency,budget_version_id,period_from,period_to")
    data_rows = rows[1:]
    assert data_rows
    budget_total = Decimal("0")
    actual_total = Decimal("0")
    for line in data_rows:
        cells = line.split(",")
        assert str(ALPHA_ORG_ID) in cells[0]
        assert cells[1] == "MXN"
        assert cells[2] == version_id
        assert cells[3] == "2026-01-01"
        budget_total += Decimal(cells[8])
        actual_total += Decimal(cells[9])
    metrics = summary_metrics(seeded_client, version_id=version_id)
    assert f"{budget_total:.4f}" == metrics["budget_amount"]
    assert f"{actual_total:.4f}" == metrics["actual_amount"]


def test_scenario_preview_matches_saved_and_leaves_source_unchanged(
    seeded_client: TestClient,
) -> None:
    version_id = create_budget_version(seeded_client, "Acceptance scenario")
    import_workbook(
        seeded_client,
        content=sample_bytes("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="ac010-budget",
    )
    expense_ids = [account_id(seeded_client, code) for code in ("6110", "6120", "6200")]
    rules = [
        {
            "sequence": 1,
            "operation": "percentage_change",
            "value": "0.0500",
            "scope": {
                "period_from": "2026-02-01",
                "period_to": "2026-03-01",
                "account_ids": expense_ids,
                "department_ids": [],
                "cost_center_ids": [],
            },
        }
    ]
    query = {
        "fiscal_year": 2026,
        "period_from": "2026-01-01",
        "period_to": "2026-03-01",
        "budget_version_id": version_id,
    }
    before = summary_metrics(
        seeded_client,
        version_id=version_id,
        period_from="2026-01-01",
        period_to="2026-03-01",
    )
    preview = seeded_client.post(
        f"{PREFIX}/scenarios/preview",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={**query, "baseline_type": "budget", "rules": rules},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["result"] != preview.json()["baseline"]
    created = seeded_client.post(
        f"{PREFIX}/scenarios",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            "name": "Más 5 por ciento gasto futuro",
            "baseline_type": "budget",
            "budget_version_id": version_id,
            "fiscal_year": 2026,
            "rules": rules,
        },
    )
    assert created.status_code == 201, created.text
    saved = seeded_client.get(
        f"{PREFIX}/scenarios/{created.json()['id']}",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert saved.status_code == 200
    replay = seeded_client.post(
        f"{PREFIX}/scenarios/preview",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={**query, "baseline_type": "budget", "rules": saved.json()["rules"]},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["baseline"] == preview.json()["baseline"]
    assert replay.json()["result"] == preview.json()["result"]
    after = summary_metrics(
        seeded_client,
        version_id=version_id,
        period_from="2026-01-01",
        period_to="2026-03-01",
    )
    assert after["budget_amount"] == before["budget_amount"]
    assert after["actual_amount"] == before["actual_amount"]
