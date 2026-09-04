# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

import time
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from budgetlens.adapters.db import session_scope
from budgetlens.application.analytics_query import parse_analytics_query
from budgetlens.dev_identities import (
    ALPHA_ANALYST_ID,
    ALPHA_ORG_ID,
    BETA_ADMIN_ID,
    BETA_ORG_ID,
)
from tests.integration.analytics_support import (
    FISCAL_YEAR,
    PERIOD_FEB,
    PERIOD_JAN,
    PERIOD_MAR,
    analytics_params,
    explain_totals,
    get_summary,
    insert_volume_rows,
    load_canonical_alpha,
    load_canonical_beta,
    lookup_id,
)
from tests.integration.import_support import PREFIX, auth_headers


@pytest.mark.integration
def test_canonical_summary_breakdown_and_edge_cases(seeded_client: TestClient) -> None:
    fixture = load_canonical_alpha(seeded_client)
    version_id = fixture["version_id"]
    january = get_summary(seeded_client, version_id)["metrics"]
    assert january["variance_percent"] is None or january["favorability"] == "unknown"
    assert january["favorability"] == "unknown"
    expense = get_summary(seeded_client, version_id, extra={"account_id": fixture["account_6110"]})[
        "metrics"
    ]
    assert expense["budget_amount"] == "100.0000"
    assert expense["actual_amount"] == "130.0000"
    assert expense["variance_amount"] == "30.0000"
    assert expense["favorability"] == "unfavorable"
    revenue = get_summary(seeded_client, version_id, extra={"account_id": fixture["account_4100"]})[
        "metrics"
    ]
    assert revenue["variance_amount"] == "50.0000"
    assert revenue["favorability"] == "favorable"
    unbounded = get_summary(
        seeded_client, version_id, extra={"account_id": fixture["account_6300"]}
    )["metrics"]
    assert unbounded["variance_percent"] is None
    assert unbounded["variance_state"] == "unbounded"
    idle = get_summary(seeded_client, version_id, extra={"account_id": fixture["account_6400"]})[
        "metrics"
    ]
    assert idle["variance_percent"] is None
    assert idle["variance_state"] == "no_activity"
    negative = get_summary(
        seeded_client, version_id, extra={"account_id": fixture["account_6120"]}
    )["metrics"]
    assert negative["actual_amount"] == "-10.0000"
    assert negative["variance_amount"] == "-60.0000"
    assert negative["favorability"] == "favorable"
    large = get_summary(
        seeded_client,
        version_id,
        extra={
            "account_id": lookup_id(
                seeded_client, "accounts", "6200", user=ALPHA_ANALYST_ID, org=ALPHA_ORG_ID
            )
        },
    )["metrics"]
    assert large["budget_amount"] == "123456789.1234"
    assert large["variance_amount"] == "0.0000"
    breakdown = seeded_client.get(
        f"{PREFIX}/analytics/variance-breakdown",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={**analytics_params(version_id), "group_by": "department", "limit": 100},
    )
    assert breakdown.status_code == 200, breakdown.text
    parts = sum(
        (Decimal(item["metrics"]["variance_amount"]) for item in breakdown.json()["items"]),
        Decimal("0"),
    )
    assert f"{parts:.4f}" == january["variance_amount"]
    top = seeded_client.get(
        f"{PREFIX}/analytics/top-unfavorable",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={**analytics_params(version_id), "group_by": "account", "limit": 10},
    )
    assert top.status_code == 200, top.text
    codes = [item["group_code"] for item in top.json()["items"]]
    assert "6110" in codes
    assert all(item["metrics"]["favorability"] == "unfavorable" for item in top.json()["items"])


@pytest.mark.integration
def test_combined_filters_and_inclusive_period_range(seeded_client: TestClient) -> None:
    fixture = load_canonical_alpha(seeded_client)
    version_id = fixture["version_id"]
    filtered = get_summary(
        seeded_client,
        version_id,
        extra={
            "account_id": fixture["account_6110"],
            "department_id": fixture["dept_ops"],
            "cost_center_id": fixture["cc_gen"],
        },
    )["metrics"]
    assert filtered["budget_amount"] == "100.0000"
    assert filtered["actual_amount"] == "130.0000"
    through_february = get_summary(
        seeded_client,
        version_id,
        period_from=PERIOD_JAN,
        period_to=PERIOD_FEB,
        extra={"account_id": fixture["account_6110"], "department_id": fixture["dept_ops"]},
    )["metrics"]
    assert through_february["budget_amount"] == "180.0000"
    through_march = get_summary(
        seeded_client,
        version_id,
        period_from=PERIOD_JAN,
        period_to=PERIOD_MAR,
        extra={"account_id": fixture["account_6110"], "department_id": fixture["dept_ops"]},
    )["metrics"]
    assert through_march["budget_amount"] == "200.0000"


@pytest.mark.integration
def test_same_codes_do_not_cross_tenants(seeded_client: TestClient) -> None:
    alpha = load_canonical_alpha(seeded_client)
    beta_version = load_canonical_beta(seeded_client)
    alpha_metrics = get_summary(
        seeded_client, alpha["version_id"], extra={"account_id": alpha["account_6110"]}
    )["metrics"]
    beta_account = lookup_id(seeded_client, "accounts", "6110", user=BETA_ADMIN_ID, org=BETA_ORG_ID)
    beta_metrics = get_summary(
        seeded_client,
        beta_version,
        user=BETA_ADMIN_ID,
        org=BETA_ORG_ID,
        extra={"account_id": beta_account},
    )["metrics"]
    assert alpha_metrics["budget_amount"] == "100.0000"
    assert beta_metrics["budget_amount"] == "999.0000"
    assert alpha_metrics["actual_amount"] != beta_metrics["actual_amount"]
    leaked = seeded_client.get(
        f"{PREFIX}/analytics/variance-summary",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params=analytics_params(beta_version),
    )
    assert leaked.status_code in {403, 404}


@pytest.mark.integration
def test_stable_order_and_cursor_does_not_lose_or_duplicate(seeded_client: TestClient) -> None:
    fixture = load_canonical_alpha(seeded_client)
    version_id = fixture["version_id"]
    params = {
        **analytics_params(version_id),
        "group_by": "account",
        "sort": "absolute_variance",
        "direction": "desc",
    }
    full = seeded_client.get(
        f"{PREFIX}/analytics/variance-breakdown",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={**params, "limit": 100},
    )
    assert full.status_code == 200, full.text
    expected = [item["group_id"] for item in full.json()["items"]]
    codes = [
        item["group_code"]
        for item in full.json()["items"]
        if item["group_code"] in {"TIEA", "TIEB"}
    ]
    assert codes == ["TIEA", "TIEB"]
    collected: list[str] = []
    cursor: str | None = None
    for _ in range(20):
        page = seeded_client.get(
            f"{PREFIX}/analytics/variance-breakdown",
            headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
            params={**params, "limit": 3, **({"cursor": cursor} if cursor else {})},
        )
        assert page.status_code == 200, page.text
        body = page.json()
        collected.extend(item["group_id"] for item in body["items"])
        if not body["page"]["has_more"]:
            assert body["page"]["next_cursor"] is None
            break
        cursor = body["page"]["next_cursor"]
        assert cursor
    assert collected == expected
    assert len(collected) == len(set(collected))


@pytest.mark.integration
def test_compare_periods_and_export_match_api_and_neutralize_text(
    seeded_client: TestClient,
) -> None:
    fixture = load_canonical_alpha(seeded_client)
    version_id = fixture["version_id"]
    compared = seeded_client.get(
        f"{PREFIX}/analytics/compare-periods",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={
            **analytics_params(
                version_id,
                extra={
                    "account_id": fixture["account_6110"],
                    "department_id": fixture["dept_ops"],
                },
            ),
            "compare_from": PERIOD_FEB,
            "compare_to": PERIOD_FEB,
        },
    )
    assert compared.status_code == 200, compared.text
    assert compared.json()["baseline"]["metrics"]["budget_amount"] == "100.0000"
    assert compared.json()["comparison"]["metrics"]["budget_amount"] == "80.0000"
    created = seeded_client.post(
        f"{PREFIX}/exports",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            "filters": {
                "fiscal_year": FISCAL_YEAR,
                "period_from": PERIOD_JAN,
                "period_to": PERIOD_JAN,
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
    text_body = content.text.lstrip("\ufeff")
    assert "'=CMD" in text_body
    assert ",=CMD" not in text_body
    breakdown = seeded_client.get(
        f"{PREFIX}/analytics/variance-breakdown",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={**analytics_params(version_id), "group_by": "account", "limit": 100},
    )
    assert breakdown.status_code == 200
    api_total = sum(
        (Decimal(item["metrics"]["budget_amount"]) for item in breakdown.json()["items"]),
        Decimal("0"),
    )
    export_total = Decimal("0")
    for line in text_body.splitlines()[1:]:
        if not line:
            continue
        export_total += Decimal(line.split(",")[8])
    assert f"{export_total:.4f}" == f"{api_total:.4f}"


@pytest.mark.integration
def test_scenario_preview_save_archive_and_ordered_rules(seeded_client: TestClient) -> None:
    fixture = load_canonical_alpha(seeded_client)
    version_id = fixture["version_id"]
    query = {
        "fiscal_year": FISCAL_YEAR,
        "period_from": PERIOD_JAN,
        "period_to": PERIOD_JAN,
        "budget_version_id": version_id,
        "baseline_type": "budget",
        "account_ids": [fixture["account_6110"]],
    }
    before = get_summary(seeded_client, version_id, extra={"account_id": fixture["account_6110"]})[
        "metrics"
    ]["budget_amount"]
    zero = seeded_client.post(
        f"{PREFIX}/scenarios/preview",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            **query,
            "rules": [
                {
                    "sequence": 1,
                    "operation": "percentage_change",
                    "value": "0.0000",
                    "scope": {
                        "period_from": PERIOD_JAN,
                        "period_to": PERIOD_JAN,
                        "account_ids": [fixture["account_6110"]],
                        "department_ids": [],
                        "cost_center_ids": [],
                    },
                }
            ],
        },
    )
    assert zero.status_code == 200, zero.text
    assert zero.json()["baseline"] == before
    assert zero.json()["result"] == before
    percent = seeded_client.post(
        f"{PREFIX}/scenarios/preview",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            **query,
            "rules": [
                {
                    "sequence": 1,
                    "operation": "percentage_change",
                    "value": "0.0500",
                    "scope": {
                        "period_from": PERIOD_JAN,
                        "period_to": PERIOD_JAN,
                        "account_ids": [fixture["account_6110"]],
                        "department_ids": [],
                        "cost_center_ids": [],
                    },
                }
            ],
        },
    )
    assert percent.status_code == 200, percent.text
    assert percent.json()["result"] == "105.0000"
    overlapping = seeded_client.post(
        f"{PREFIX}/scenarios/preview",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            **query,
            "rules": [
                {
                    "sequence": 2,
                    "operation": "absolute_change",
                    "value": "10.0000",
                    "scope": {
                        "period_from": PERIOD_JAN,
                        "period_to": PERIOD_JAN,
                        "account_ids": [fixture["account_6110"]],
                        "department_ids": [],
                        "cost_center_ids": [],
                    },
                },
                {
                    "sequence": 1,
                    "operation": "percentage_change",
                    "value": "0.0500",
                    "scope": {
                        "period_from": PERIOD_JAN,
                        "period_to": PERIOD_JAN,
                        "account_ids": [fixture["account_6110"]],
                        "department_ids": [],
                        "cost_center_ids": [],
                    },
                },
            ],
        },
    )
    assert overlapping.status_code == 200, overlapping.text
    assert overlapping.json()["result"] == "115.0000"
    created = seeded_client.post(
        f"{PREFIX}/scenarios",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            "name": "Más cinco por ciento",
            "baseline_type": "budget",
            "budget_version_id": version_id,
            "fiscal_year": FISCAL_YEAR,
            "rules": [
                {
                    "sequence": 1,
                    "operation": "percentage_change",
                    "value": "0.0500",
                    "scope": {
                        "period_from": PERIOD_JAN,
                        "period_to": PERIOD_JAN,
                        "account_ids": [fixture["account_6110"]],
                        "department_ids": [],
                        "cost_center_ids": [],
                    },
                }
            ],
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
        json={**query, "rules": saved.json()["rules"]},
    )
    assert replay.status_code == 200
    assert replay.json()["result"] == percent.json()["result"]
    archived = seeded_client.post(
        f"{PREFIX}/scenarios/{created.json()['id']}/archive",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
    after = get_summary(seeded_client, version_id, extra={"account_id": fixture["account_6110"]})[
        "metrics"
    ]["budget_amount"]
    assert after == before


@pytest.mark.integration
def test_summary_explain_uses_tenant_period_index(seeded_client: TestClient) -> None:
    fixture = load_canonical_alpha(seeded_client)
    insert_volume_rows(
        job_id=fixture["job_id"],
        organization_id=ALPHA_ORG_ID,
        version_id=fixture["version_id"],
        account_id=fixture["account_6110"],
        department_id=fixture["dept_ops"],
        cost_center_id=fixture["cc_gen"],
        count=4_000,
    )
    query = parse_analytics_query(
        fiscal_year=FISCAL_YEAR,
        period_from=date_from(PERIOD_JAN),
        period_to=date_from(PERIOD_MAR),
        budget_version_id=UUID(fixture["version_id"]),
    )
    with session_scope() as session:
        session.execute(text("SET LOCAL enable_seqscan = off"))
        plan = explain_totals(session, ALPHA_ORG_ID, query)
    assert "ix_financial_entries" in plan
    started = time.perf_counter()
    summary = get_summary(
        seeded_client, fixture["version_id"], period_from=PERIOD_JAN, period_to=PERIOD_MAR
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert summary["metrics"]["budget_amount"]
    assert elapsed_ms < 500


def date_from(value: str):
    from datetime import date

    return date.fromisoformat(value)
