from __future__ import annotations

import hashlib
import io
from decimal import Decimal
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
from tests.integration.import_support import (
    CANONICAL,
    PREFIX,
    entry_count_for_job,
    overwrite_job_object,
)
from tests.integration.import_support import (
    account_id as _account_id,
)
from tests.integration.import_support import (
    auth_headers as _headers,
)
from tests.integration.import_support import (
    create_budget_version as _create_version,
)
from tests.integration.import_support import (
    import_workbook as _import_file,
)
from tests.integration.import_support import (
    sample_bytes as _read,
)


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
    assert entry_count_for_job(str(result["id"])) == 0


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
    deleted = seeded_client.delete(
        f"{PREFIX}/conversations/{conversation_id}",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert deleted.status_code == 200
    missing = seeded_client.get(
        f"{PREFIX}/conversations/{conversation_id}",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert missing.status_code == 404
    audits = seeded_client.get(
        f"{PREFIX}/audit-events",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        params={"action": "conversation.deleted"},
    )
    assert audits.status_code == 200
    events = audits.json()["items"]
    assert events
    assert events[0]["metadata"]["deleted"] is True
    assert "content" not in events[0]["metadata"]
    assert "prompt" not in str(events[0]["metadata"]).lower()


@pytest.mark.integration
def test_export_download_is_authorized_and_expires(seeded_client: TestClient) -> None:
    from datetime import UTC, datetime, timedelta

    from budgetlens.adapters.db import session_scope
    from budgetlens.adapters.persistence.models import ExportJobRow

    version_id = _create_version(seeded_client, "ExportExpire")
    _import_file(
        seeded_client,
        content=_read("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="export-budget",
    )
    seeded_client.post(
        f"{PREFIX}/budget-versions/{version_id}/publish",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "pub-ex"),
    )
    created = seeded_client.post(
        f"{PREFIX}/exports",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
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
    export_id = created.json()["id"]
    allowed = seeded_client.get(
        f"{PREFIX}/exports/{export_id}/content",
        headers=_headers(ALPHA_VIEWER_ID, ALPHA_ORG_ID),
    )
    assert allowed.status_code == 200
    cross = seeded_client.get(
        f"{PREFIX}/exports/{export_id}/content",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
    )
    assert cross.status_code == 404
    with session_scope() as session:
        row = session.get(ExportJobRow, UUID(export_id))
        assert row is not None
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    expired = seeded_client.get(
        f"{PREFIX}/exports/{export_id}/content",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert expired.status_code == 404


@pytest.mark.integration
def test_import_contract_fixtures_cover_normalization_and_preview(
    seeded_client: TestClient,
) -> None:
    version_id = _create_version(seeded_client, "Contract")
    leading = _import_file(
        seeded_client,
        content=_read("leading-zero.csv"),
        filename="leading-zero.csv",
        import_type="budget",
        version_id=version_id,
        commit=False,
        user=ALPHA_ADMIN_ID,
        mapping={**CANONICAL, "account_name": "account_name"},
    )
    confirmed = seeded_client.post(
        f"{PREFIX}/imports/{leading['id']}/validate",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        json={
            "mapping": {**CANONICAL, "account_name": "account_name"},
            "create_missing_dimensions": True,
        },
    )
    assert confirmed.status_code == 200
    leading = confirmed.json()
    assert leading["status"] == "ready"
    preview = seeded_client.get(
        f"{PREFIX}/imports/{leading['id']}/preview",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        params={"limit": 50},
    )
    assert preview.status_code == 200
    body = preview.json()
    assert body["sha256_short"] == leading["sha256"][:12]
    assert body["items"][0]["account_code"] == "0610"
    assert body["replaced_records"] == 0
    assert body["job"]["valid_amount_total"] == leading["valid_amount_total"]
    locale = _import_file(
        seeded_client,
        content=_read("locale-ambiguous.csv"),
        filename="locale-ambiguous.csv",
        import_type="budget",
        version_id=_create_version(seeded_client, "Locale"),
        commit=False,
        mapping=CANONICAL,
    )
    assert locale["status"] == "invalid"
    locale_ready = seeded_client.post(
        f"{PREFIX}/imports/{locale['id']}/validate",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"mapping": CANONICAL, "create_missing_dimensions": False, "amount_locale": "es"},
    )
    assert locale_ready.status_code == 200
    assert locale_ready.json()["status"] == "ready"
    duplicates = _import_file(
        seeded_client,
        content=_read("duplicates.csv"),
        filename="duplicates.csv",
        import_type="budget",
        version_id=_create_version(seeded_client, "Dup"),
        commit=False,
    )
    assert duplicates["status"] == "invalid"
    dup_errors = seeded_client.get(
        f"{PREFIX}/imports/{duplicates['id']}/errors",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    ).json()["items"]
    assert any(item["code"] == "DUPLICATE_ROW" for item in dup_errors)
    unknown = _import_file(
        seeded_client,
        content=_read("unknown-dimension.csv"),
        filename="unknown-dimension.csv",
        import_type="budget",
        version_id=_create_version(seeded_client, "Unknown"),
        commit=False,
    )
    assert unknown["status"] == "invalid"
    unknown_errors = seeded_client.get(
        f"{PREFIX}/imports/{unknown['id']}/errors",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    ).json()["items"]
    assert any(item["code"] == "UNKNOWN_ACCOUNT" for item in unknown_errors)
    xlsx = _import_file(
        seeded_client,
        content=_read("budget-valid.xlsx"),
        filename="budget-valid.xlsx",
        import_type="budget",
        version_id=_create_version(seeded_client, "XlsxFixture"),
        idempotency="xlsx-fixture",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert xlsx["_status"] == 200
    formula = _import_file(
        seeded_client,
        content=_read("formula.xlsx"),
        filename="formula.xlsx",
        import_type="budget",
        version_id=_create_version(seeded_client, "FormulaFixture"),
        commit=False,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    assert formula["status"] == "invalid"
    fingerprint_content = (
        b"period,account_code,department_code,cost_center_code,amount,currency\n"
        b"2026-01,6100,OPS,CC-GEN,1111.0000,MXN\n"
    )
    applied_version = _create_version(seeded_client, "AppliedOnce")
    first = _import_file(
        seeded_client,
        content=fingerprint_content,
        filename="applied-once.csv",
        import_type="budget",
        version_id=applied_version,
        commit=True,
        idempotency="applied-once",
    )
    assert first["_status"] == 200
    replay = _import_file(
        seeded_client,
        content=fingerprint_content,
        filename="applied-once.csv",
        import_type="budget",
        version_id=applied_version,
        commit=False,
        idempotency="applied-twice",
    )
    assert replay["id"] == first["_body"]["id"]
    assert replay["status"] == "applied"


def _upload_only(
    client: TestClient,
    *,
    content: bytes,
    filename: str,
    import_type: str,
    version_id: str | None,
    user: UUID = ALPHA_ANALYST_ID,
    org: UUID = ALPHA_ORG_ID,
    media_type: str = "text/csv",
) -> str:
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
        },
    )
    assert created.status_code == 201, created.text
    job_id = str(created.json()["id"])
    uploaded = client.put(
        f"{PREFIX}/imports/{job_id}/content",
        headers={**_headers(user, org), "Content-Type": media_type},
        content=content,
    )
    assert uploaded.status_code == 200, uploaded.text
    return job_id


@pytest.mark.integration
def test_preview_after_upload_shows_sanitized_source_rows(seeded_client: TestClient) -> None:
    version_id = _create_version(seeded_client, "Inspect")
    content = _read("budget-valid.csv")
    job_id = _upload_only(
        seeded_client,
        content=content,
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
    )
    preview = seeded_client.get(
        f"{PREFIX}/imports/{job_id}/preview",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert "period" in body["headers"]
    assert body["proposed_mapping"]["period"] == "period"
    assert body["items"]
    assert body["items"][0]["period"] == "2026-01"
    assert body["job"]["status"] == "uploaded"
    assert entry_count_for_job(job_id) == 0


@pytest.mark.integration
def test_hash_change_after_validate_rejects_commit(seeded_client: TestClient) -> None:
    version_id = _create_version(seeded_client, "Hash change")
    ready = _import_file(
        seeded_client,
        content=_read("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        commit=False,
    )
    assert ready["status"] == "ready"
    overwrite_job_object(str(ready["id"]), b"tampered-after-validate")
    blocked = seeded_client.post(
        f"{PREFIX}/imports/{ready['id']}/commit",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "hash-changed"),
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "IMPORT_HASH_MISMATCH"
    assert entry_count_for_job(str(ready["id"])) == 0
    still_ready = seeded_client.get(
        f"{PREFIX}/imports/{ready['id']}",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert still_ready.json()["status"] == "ready"


@pytest.mark.integration
def test_unknown_dimension_flag_depends_on_role(seeded_client: TestClient) -> None:
    content = (
        b"period,account_code,account_name,account_type,department_code,"
        b"department_name,cost_center_code,amount,currency\n"
        b"2026-01,9999,Nueva cuenta,expense,OPS,Operaciones,CC-GEN,1000.0000,MXN\n"
    )
    mapping = {
        **CANONICAL,
        "account_name": "account_name",
        "account_type": "account_type",
        "department_name": "department_name",
    }
    analyst_job = _upload_only(
        seeded_client,
        content=content,
        filename="new-account.csv",
        import_type="budget",
        version_id=_create_version(seeded_client, "Unknown analyst"),
    )
    analyst = seeded_client.post(
        f"{PREFIX}/imports/{analyst_job}/validate",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={"mapping": mapping, "create_missing_dimensions": True},
    )
    assert analyst.status_code == 200
    assert analyst.json()["status"] == "invalid"
    analyst_errors = seeded_client.get(
        f"{PREFIX}/imports/{analyst_job}/errors",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    ).json()["items"]
    assert any(
        item["code"] == "UNKNOWN_ACCOUNT" and item["severity"] == "error" for item in analyst_errors
    )
    admin_job = _upload_only(
        seeded_client,
        content=content,
        filename="new-account.csv",
        import_type="budget",
        version_id=_create_version(seeded_client, "Unknown admin"),
        user=ALPHA_ADMIN_ID,
    )
    admin = seeded_client.post(
        f"{PREFIX}/imports/{admin_job}/validate",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
        json={"mapping": mapping, "create_missing_dimensions": True},
    )
    assert admin.status_code == 200
    assert admin.json()["status"] == "ready"
    admin_errors = seeded_client.get(
        f"{PREFIX}/imports/{admin_job}/errors",
        headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID),
    ).json()["items"]
    assert any(
        item["code"] == "UNKNOWN_ACCOUNT" and item["severity"] == "warning" for item in admin_errors
    )


@pytest.mark.integration
def test_preview_totals_match_commit_totals(seeded_client: TestClient) -> None:
    version_id = _create_version(seeded_client, "Preview totals")
    ready = _import_file(
        seeded_client,
        content=_read("budget-valid.csv"),
        filename="budget-valid.csv",
        import_type="budget",
        version_id=version_id,
        commit=False,
    )
    preview = seeded_client.get(
        f"{PREFIX}/imports/{ready['id']}/preview",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert preview.status_code == 200
    assert preview.json()["job"]["valid_amount_total"] == ready["valid_amount_total"]
    assert preview.json()["job"]["valid_count"] == ready["valid_count"]
    committed = seeded_client.post(
        f"{PREFIX}/imports/{ready['id']}/commit",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID, "preview-equals-commit"),
    )
    assert committed.status_code == 200
    assert committed.json()["valid_amount_total"] == ready["valid_amount_total"]
    assert committed.json()["valid_count"] == ready["valid_count"]
    assert entry_count_for_job(str(ready["id"])) == ready["valid_count"]


@pytest.mark.integration
def test_error_report_neutralizes_csv_injection(seeded_client: TestClient) -> None:
    content = (
        b"period,account_code,department_code,cost_center_code,amount,currency\n"
        b"2026-01,=CMD,OPS,CC-GEN,10.0000,MXN\n"
    )
    job = _import_file(
        seeded_client,
        content=content,
        filename="inject.csv",
        import_type="budget",
        version_id=_create_version(seeded_client, "Injection"),
        commit=False,
    )
    report = seeded_client.get(
        f"{PREFIX}/imports/{job['id']}/error-report",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
    )
    assert report.status_code == 200
    text = report.content.decode("utf-8")
    assert "'=CMD" in text
    assert ",=CMD" not in text


@pytest.mark.integration
def test_alpha_cannot_read_beta_import_objects(seeded_client: TestClient) -> None:
    content = (
        b"period,account_code,department_code,cost_center_code,amount,currency\n"
        b"2026-01,6100,OPS,CC-GEN,10.0000,USD\n"
    )
    beta_version = seeded_client.post(
        f"{PREFIX}/budget-versions",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"name": "Beta objects", "fiscal_year": 2026},
    )
    assert beta_version.status_code == 201
    job_id = _upload_only(
        seeded_client,
        content=content,
        filename="beta.csv",
        import_type="budget",
        version_id=str(beta_version.json()["id"]),
        user=BETA_ADMIN_ID,
        org=BETA_ORG_ID,
    )
    seeded_client.post(
        f"{PREFIX}/imports/{job_id}/validate",
        headers=_headers(BETA_ADMIN_ID, BETA_ORG_ID),
        json={"mapping": CANONICAL, "create_missing_dimensions": False},
    )
    for path, method in (
        (f"{PREFIX}/imports/{job_id}/preview", "GET"),
        (f"{PREFIX}/imports/{job_id}/errors", "GET"),
        (f"{PREFIX}/imports/{job_id}/error-report", "GET"),
        (f"{PREFIX}/imports/{job_id}/content", "PUT"),
    ):
        if method == "PUT":
            response = seeded_client.put(
                path,
                headers={**_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID), "Content-Type": "text/csv"},
                content=content,
            )
        else:
            response = seeded_client.get(path, headers=_headers(ALPHA_ADMIN_ID, ALPHA_ORG_ID))
        assert response.status_code in {403, 404}, path


@pytest.mark.integration
def test_invalid_mime_and_size_are_rejected(seeded_client: TestClient) -> None:
    content = _read("budget-valid.csv")
    version_id = _create_version(seeded_client, "Rejected file")
    digest = hashlib.sha256(content).hexdigest()
    oversized = seeded_client.post(
        f"{PREFIX}/imports",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            "import_type": "budget",
            "budget_version_id": version_id,
            "original_filename": "budget-valid.csv",
            "size_bytes": 30 * 1024 * 1024,
            "sha256": digest,
        },
    )
    assert oversized.status_code == 413
    created = seeded_client.post(
        f"{PREFIX}/imports",
        headers=_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        json={
            "import_type": "budget",
            "budget_version_id": version_id,
            "original_filename": "budget-valid.csv",
            "size_bytes": len(content),
            "sha256": digest,
        },
    )
    assert created.status_code == 201
    wrong_mime = seeded_client.put(
        f"{PREFIX}/imports/{created.json()['id']}/content",
        headers={**_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID), "Content-Type": "application/pdf"},
        content=content,
    )
    assert wrong_mime.status_code == 422
    assert wrong_mime.json()["error"]["code"] == "UNSUPPORTED_FILE"
