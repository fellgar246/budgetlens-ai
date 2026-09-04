# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from budgetlens.adapters.db import session_scope
from budgetlens.adapters.persistence.finance_repositories import SqlAnalyticsRepository
from budgetlens.adapters.persistence.models import FinancialEntryRow
from budgetlens.application.analytics_query import AnalyticsQuery
from budgetlens.dev_identities import (
    ALPHA_ADMIN_ID,
    ALPHA_ANALYST_ID,
    ALPHA_ORG_ID,
    BETA_ADMIN_ID,
    BETA_ORG_ID,
)
from tests.integration.import_support import PREFIX, auth_headers, import_workbook

FISCAL_YEAR = 2027
PERIOD_JAN = "2027-01-01"
PERIOD_FEB = "2027-02-01"
PERIOD_MAR = "2027-03-01"


def csv_rows(rows: list[str], *, currency: str = "MXN") -> bytes:
    header = "period,account_code,department_code,cost_center_code,amount,currency"
    body = [header, *[f"{row},{currency}" for row in rows], ""]
    return "\n".join(body).encode("utf-8")


def create_version(
    client: TestClient,
    name: str,
    *,
    user: UUID = ALPHA_ANALYST_ID,
    org: UUID = ALPHA_ORG_ID,
    fiscal_year: int = FISCAL_YEAR,
) -> str:
    created = client.post(
        f"{PREFIX}/budget-versions",
        headers=auth_headers(user, org),
        json={"name": name, "fiscal_year": fiscal_year},
    )
    assert created.status_code == 201, created.text
    return str(created.json()["id"])


def create_account(
    client: TestClient,
    *,
    code: str,
    name: str,
    account_type: str = "expense",
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


def lookup_id(
    client: TestClient,
    path: str,
    code: str,
    *,
    user: UUID,
    org: UUID,
) -> str:
    listed = client.get(f"{PREFIX}/{path}", headers=auth_headers(user, org), params={"limit": 100})
    assert listed.status_code == 200, listed.text
    for item in listed.json()["items"]:
        if item["code"] == code:
            return str(item["id"])
    raise AssertionError(f"{path} {code}")


def analytics_params(
    version_id: str,
    *,
    period_from: str = PERIOD_JAN,
    period_to: str = PERIOD_JAN,
    extra: dict[str, str | int] | None = None,
) -> dict[str, str | int]:
    payload: dict[str, str | int] = {
        "fiscal_year": FISCAL_YEAR,
        "period_from": period_from,
        "period_to": period_to,
        "budget_version_id": version_id,
    }
    if extra:
        payload.update(extra)
    return payload


def get_summary(
    client: TestClient,
    version_id: str,
    *,
    user: UUID = ALPHA_ANALYST_ID,
    org: UUID = ALPHA_ORG_ID,
    period_from: str = PERIOD_JAN,
    period_to: str = PERIOD_JAN,
    extra: dict[str, str | int] | None = None,
) -> dict[str, Any]:
    response = client.get(
        f"{PREFIX}/analytics/variance-summary",
        headers=auth_headers(user, org),
        params=analytics_params(
            version_id, period_from=period_from, period_to=period_to, extra=extra
        ),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert isinstance(body, dict)
    return {str(key): value for key, value in body.items()}


def load_canonical_alpha(client: TestClient) -> dict[str, str]:
    create_account(client, code="INJ1", name="=CMD", account_type="expense")
    for index in range(1, 7):
        create_account(
            client, code=f"PG{index:02d}", name=f"Page {index:02d}", account_type="expense"
        )
    create_account(client, code="TIEA", name="Tie A", account_type="expense")
    create_account(client, code="TIEB", name="Tie B", account_type="expense")
    version_id = create_version(client, "Canonical Alpha 2027")
    budget = csv_rows(
        [
            "2027-01,6110,OPS,CC-GEN,100.0000",
            "2027-01,4100,SALES,CC-GEN,200.0000",
            "2027-01,6300,OPS,CC-GEN,0.0000",
            "2027-01,6400,OPS,CC-GEN,0.0000",
            "2027-01,6120,OPS,CC-GEN,50.0000",
            "2027-01,6200,OPS,CC-GEN,123456789.1234",
            "2027-01,INJ1,OPS,CC-GEN,10.0000",
            "2027-01,TIEA,OPS,CC-GEN,10.0000",
            "2027-01,TIEB,OPS,CC-GEN,10.0000",
            "2027-02,6110,OPS,CC-GEN,80.0000",
            "2027-02,6110,FIN,CC-GEN,40.0000",
            "2027-03,6110,OPS,CC-GEN,20.0000",
            *[f"2027-01,PG{index:02d},OPS,CC-GEN,{Decimal(index)}.0000" for index in range(1, 7)],
        ]
    )
    actuals = csv_rows(
        [
            "2027-01,6110,OPS,CC-GEN,130.0000",
            "2027-01,4100,SALES,CC-GEN,250.0000",
            "2027-01,6300,OPS,CC-GEN,25.0000",
            "2027-01,6400,OPS,CC-GEN,0.0000",
            "2027-01,6120,OPS,CC-GEN,-10.0000",
            "2027-01,6200,OPS,CC-GEN,123456789.1234",
            "2027-01,INJ1,OPS,CC-GEN,10.0000",
            "2027-01,TIEA,OPS,CC-GEN,25.0000",
            "2027-01,TIEB,OPS,CC-GEN,25.0000",
            "2027-02,6110,OPS,CC-GEN,80.0000",
            "2027-02,6110,FIN,CC-GEN,10.0000",
            "2027-03,6110,OPS,CC-GEN,20.0000",
            *[
                f"2027-01,PG{index:02d},OPS,CC-GEN,{Decimal(index) + Decimal('0.5000')}"
                for index in range(1, 7)
            ],
        ]
    )
    budget_job = import_workbook(
        client,
        content=budget,
        filename="canonical-budget.csv",
        import_type="budget",
        version_id=version_id,
        idempotency="canonical-alpha-budget",
    )
    assert budget_job["_status"] == 200, budget_job
    actual_job = import_workbook(
        client,
        content=actuals,
        filename="canonical-actuals.csv",
        import_type="actual",
        version_id=None,
        idempotency="canonical-alpha-actual",
    )
    assert actual_job["_status"] == 200, actual_job
    ids = {
        "6110": "account_6110",
        "4100": "account_4100",
        "6300": "account_6300",
        "6400": "account_6400",
        "6120": "account_6120",
    }
    resolved = {
        key: lookup_id(client, "accounts", code, user=ALPHA_ANALYST_ID, org=ALPHA_ORG_ID)
        for code, key in ids.items()
    }
    return {
        "version_id": version_id,
        "job_id": str(budget_job["_body"]["id"]),
        **resolved,
        "dept_ops": lookup_id(
            client, "departments", "OPS", user=ALPHA_ANALYST_ID, org=ALPHA_ORG_ID
        ),
        "dept_sales": lookup_id(
            client, "departments", "SALES", user=ALPHA_ANALYST_ID, org=ALPHA_ORG_ID
        ),
        "cc_gen": lookup_id(
            client, "cost-centers", "CC-GEN", user=ALPHA_ANALYST_ID, org=ALPHA_ORG_ID
        ),
    }


def load_canonical_beta(client: TestClient) -> str:
    version_id = create_version(client, "Canonical Beta 2027", user=BETA_ADMIN_ID, org=BETA_ORG_ID)
    budget = csv_rows(["2027-01,6110,OPS,CC-GEN,999.0000"], currency="USD")
    actuals = csv_rows(["2027-01,6110,OPS,CC-GEN,1.0000"], currency="USD")
    budget_job = import_workbook(
        client,
        content=budget,
        filename="canonical-beta-budget.csv",
        import_type="budget",
        version_id=version_id,
        user=BETA_ADMIN_ID,
        org=BETA_ORG_ID,
        idempotency="canonical-beta-budget",
    )
    assert budget_job["_status"] == 200, budget_job
    actual_job = import_workbook(
        client,
        content=actuals,
        filename="canonical-beta-actuals.csv",
        import_type="actual",
        version_id=None,
        user=BETA_ADMIN_ID,
        org=BETA_ORG_ID,
        idempotency="canonical-beta-actual",
    )
    assert actual_job["_status"] == 200, actual_job
    return version_id


def explain_totals(session: Session, organization_id: UUID, query: AnalyticsQuery) -> str:
    statement = SqlAnalyticsRepository(session, organization_id).totals_statement(query)
    compiled = statement.compile(
        dialect=session.get_bind().dialect,
        compile_kwargs={"literal_binds": True},
    )
    rows = session.execute(text(f"EXPLAIN (FORMAT TEXT) {compiled}")).all()
    return "\n".join(str(row[0]) for row in rows)


def insert_volume_rows(
    *,
    job_id: str,
    organization_id: UUID,
    version_id: str,
    account_id: str,
    department_id: str,
    cost_center_id: str,
    count: int,
) -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    now = datetime.now(UTC)
    payload: list[dict[str, object]] = []
    for index in range(count):
        month = (index % 12) + 1
        is_budget = index % 2 == 0
        payload.append(
            {
                "id": uuid4(),
                "organization_id": organization_id,
                "import_job_id": UUID(job_id),
                "scenario_type": "budget" if is_budget else "actual",
                "budget_version_id": UUID(version_id) if is_budget else None,
                "period_start": date(2027, month, 1),
                "fiscal_year": FISCAL_YEAR,
                "account_id": UUID(account_id),
                "department_id": UUID(department_id),
                "cost_center_id": UUID(cost_center_id),
                "amount": Decimal("1.0000"),
                "currency": "MXN",
                "source_row_number": 20_000 + index,
                "source_reference": None,
                "created_at": now,
            }
        )
    with session_scope() as session:
        session.execute(insert(FinancialEntryRow), payload)
