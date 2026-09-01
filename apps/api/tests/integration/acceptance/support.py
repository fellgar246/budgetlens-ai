# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from budgetlens.adapters.db import session_scope
from budgetlens.adapters.persistence.models import FinancialEntryRow
from budgetlens.dev_identities import ALPHA_ADMIN_ID, ALPHA_ANALYST_ID, ALPHA_ORG_ID
from tests.integration.import_support import (
    CANONICAL,
    PREFIX,
    account_id,
    auth_headers,
    create_budget_version,
    import_workbook,
    sample_bytes,
)

__all__ = [
    "CANONICAL",
    "PREFIX",
    "account_id",
    "active_budget_version",
    "ask_copilot",
    "auth_headers",
    "create_account",
    "create_budget_version",
    "create_conversation",
    "entry_count",
    "import_workbook",
    "sample_bytes",
    "sensitive_leak",
    "summary_metrics",
]


def create_account(
    client: TestClient,
    *,
    code: str,
    name: str,
    account_type: str,
    user: UUID = ALPHA_ADMIN_ID,
    org: UUID = ALPHA_ORG_ID,
) -> str:
    created = client.post(
        f"{PREFIX}/accounts",
        headers=auth_headers(user, org),
        json={"code": code, "name": name, "account_type": account_type},
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def active_budget_version(client: TestClient, fiscal_year: int = 2026) -> str:
    listed = client.get(
        f"{PREFIX}/budget-versions",
        headers=auth_headers(ALPHA_ANALYST_ID, ALPHA_ORG_ID),
        params={"fiscal_year": fiscal_year},
    )
    assert listed.status_code == 200, listed.text
    items = listed.json()["items"]
    for item in items:
        if item.get("is_active"):
            return str(item["id"])
    if items:
        return str(items[0]["id"])
    return create_budget_version(client, "Acceptance AI version", fiscal_year)


def summary_metrics(
    client: TestClient,
    *,
    version_id: str,
    period_from: str = "2026-01-01",
    period_to: str = "2026-01-01",
    fiscal_year: int = 2026,
    account: str | None = None,
    department: str | None = None,
    user: UUID = ALPHA_ANALYST_ID,
    org: UUID = ALPHA_ORG_ID,
) -> dict[str, Any]:
    params: dict[str, str | int] = {
        "fiscal_year": fiscal_year,
        "period_from": period_from,
        "period_to": period_to,
        "budget_version_id": version_id,
    }
    if account:
        params["account_id"] = account
    if department:
        params["department_id"] = department
    response = client.get(
        f"{PREFIX}/analytics/variance-summary",
        headers=auth_headers(user, org),
        params=params,
    )
    assert response.status_code == 200, response.text
    payload = response.json()["metrics"]
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def entry_count(*, job_id: str | None = None, organization_id: UUID | None = None) -> int:
    with session_scope() as session:
        stmt = select(func.count()).select_from(FinancialEntryRow)
        if job_id is not None:
            stmt = stmt.where(FinancialEntryRow.import_job_id == UUID(job_id))
        if organization_id is not None:
            stmt = stmt.where(FinancialEntryRow.organization_id == organization_id)
        return int(session.scalar(stmt) or 0)


def create_conversation(
    client: TestClient,
    *,
    version_id: str,
    title: str = "Consulta",
    period_from: str = "2026-01-01",
    period_to: str = "2026-03-01",
    fiscal_year: int = 2026,
    user: UUID = ALPHA_ANALYST_ID,
    org: UUID = ALPHA_ORG_ID,
) -> str:
    created = client.post(
        f"{PREFIX}/conversations",
        headers=auth_headers(user, org),
        json={
            "title": title,
            "context": {
                "fiscal_year": fiscal_year,
                "period_from": period_from,
                "period_to": period_to,
                "budget_version_id": version_id,
                "currency": "MXN",
            },
        },
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def ask_copilot(
    client: TestClient,
    *,
    conversation_id: str,
    version_id: str,
    content: str,
    period_from: str = "2026-01-01",
    period_to: str = "2026-03-01",
    fiscal_year: int = 2026,
    user: UUID = ALPHA_ANALYST_ID,
    org: UUID = ALPHA_ORG_ID,
) -> dict[str, Any]:
    asked = client.post(
        f"{PREFIX}/conversations/{conversation_id}/messages",
        headers=auth_headers(user, org),
        json={
            "content": content,
            "context": {
                "fiscal_year": fiscal_year,
                "period_from": period_from,
                "period_to": period_to,
                "budget_version_id": version_id,
                "currency": "MXN",
            },
        },
    )
    assert asked.status_code == 200, asked.text
    payload = asked.json()
    assert isinstance(payload, dict)
    return cast(dict[str, Any], payload)


def sensitive_leak(payload: object) -> bool:
    rendered = str(payload).lower()
    markers = (
        "postgresql://",
        "bearer ",
        "password",
        "super-secret",
        "budgetlens_local_only",
        "prompt",
        "authorization",
    )
    return any(marker in rendered for marker in markers)
