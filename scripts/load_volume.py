#!/usr/bin/env python3
"""Insert synthetic ledger rows for local read-path measurement. Prints counts, not amounts."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import insert, select, text

from budgetlens.adapters.db import session_scope
from budgetlens.adapters.persistence.models import (
    AccountRow,
    BudgetVersionRow,
    CostCenterRow,
    DepartmentRow,
    FinancialEntryRow,
    ImportJobRow,
    OrganizationRow,
)
from budgetlens.dev_identities import ALPHA_ORG_ID

VOLUME_MARKER = "volume-load"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=250_000)
    parser.add_argument("--fiscal-year", type=int, default=2026)
    parser.add_argument("--batch-size", type=int, default=2_000)
    args = parser.parse_args()
    now = datetime.now(UTC)
    with session_scope() as session:
        org = session.execute(
            select(OrganizationRow).where(OrganizationRow.id == ALPHA_ORG_ID)
        ).scalar_one_or_none()
        if org is None:
            raise SystemExit("Seed Alpha before loading volume rows.")
        version = session.execute(
            select(BudgetVersionRow)
            .where(
                BudgetVersionRow.organization_id == ALPHA_ORG_ID,
                BudgetVersionRow.name == "Budget Final",
            )
            .limit(1)
        ).scalar_one_or_none()
        account = session.execute(
            select(AccountRow).where(
                AccountRow.organization_id == ALPHA_ORG_ID,
                AccountRow.code == "6110",
            )
        ).scalar_one_or_none()
        department = session.execute(
            select(DepartmentRow).where(
                DepartmentRow.organization_id == ALPHA_ORG_ID,
                DepartmentRow.code == "OPS",
            )
        ).scalar_one_or_none()
        cost_center = session.execute(
            select(CostCenterRow).where(
                CostCenterRow.organization_id == ALPHA_ORG_ID,
                CostCenterRow.code == "CC-GEN",
            )
        ).scalar_one_or_none()
        job = session.execute(
            select(ImportJobRow)
            .where(ImportJobRow.organization_id == ALPHA_ORG_ID)
            .limit(1)
        ).scalar_one_or_none()
        if version is None or account is None or department is None or cost_center is None:
            raise SystemExit("Seed catalog and Budget Final before loading volume rows.")
        if job is None:
            raise SystemExit("Seed at least one import job before loading volume rows.")
        existing = session.execute(
            text(
                "SELECT count(*) FROM financial_entries "
                "WHERE organization_id = :org AND source_reference = :marker"
            ),
            {"org": str(ALPHA_ORG_ID), "marker": VOLUME_MARKER},
        ).scalar_one()
        remaining = max(0, args.rows - int(existing))
        inserted = 0
        while inserted < remaining:
            batch = min(args.batch_size, remaining - inserted)
            payload: list[dict[str, object]] = []
            for index in range(batch):
                absolute = int(existing) + inserted + index
                month = (absolute % 12) + 1
                is_budget = absolute % 2 == 0
                payload.append(
                    {
                        "id": uuid4(),
                        "organization_id": ALPHA_ORG_ID,
                        "import_job_id": job.id,
                        "scenario_type": "budget" if is_budget else "actual",
                        "budget_version_id": version.id if is_budget else None,
                        "period_start": date(args.fiscal_year, month, 1),
                        "fiscal_year": args.fiscal_year,
                        "account_id": account.id,
                        "department_id": department.id,
                        "cost_center_id": cost_center.id,
                        "amount": Decimal("1.0000"),
                        "currency": org.functional_currency,
                        "source_row_number": 50_000 + absolute,
                        "source_reference": VOLUME_MARKER,
                        "created_at": now,
                    }
                )
            session.execute(insert(FinancialEntryRow), payload)
            inserted += batch
        total = int(existing) + inserted
    print(
        json.dumps(
            {
                "organization": "alpha",
                "requested_rows": args.rows,
                "inserted": inserted,
                "volume_rows": total,
                "fiscal_year": args.fiscal_year,
            }
        )
    )


if __name__ == "__main__":
    main()
