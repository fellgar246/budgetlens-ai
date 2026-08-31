from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from budgetlens.domain.enums import ScenarioType
from budgetlens.domain.errors import ValidationError
from budgetlens.domain.financial_entry import FinancialEntry
from budgetlens.domain.money import Currency, MoneyAmount


def _entry(
    *,
    period_start: date = date(2026, 1, 1),
    scenario_type: ScenarioType = ScenarioType.ACTUAL,
    budget_version_id: UUID | None = None,
) -> FinancialEntry:
    return FinancialEntry(
        id=UUID(int=1),
        organization_id=UUID(int=2),
        import_job_id=UUID(int=3),
        scenario_type=scenario_type,
        budget_version_id=budget_version_id,
        period_start=period_start,
        fiscal_year=2026,
        account_id=UUID(int=4),
        department_id=UUID(int=5),
        cost_center_id=UUID(int=6),
        amount=MoneyAmount("10"),
        currency=Currency("MXN"),
        source_row_number=1,
        source_reference=None,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_actual_entry_rejects_budget_version() -> None:
    with pytest.raises(ValidationError) as exc:
        _entry(budget_version_id=UUID(int=9))
    assert exc.value.code == "BUDGET_VERSION_FORBIDDEN"


def test_budget_entry_requires_version_and_month_start() -> None:
    with pytest.raises(ValidationError) as missing:
        _entry(scenario_type=ScenarioType.BUDGET)
    assert missing.value.code == "BUDGET_VERSION_REQUIRED"
    with pytest.raises(ValidationError) as period:
        _entry(period_start=date(2026, 1, 15))
    assert period.value.code == "INVALID_PERIOD"
    created = _entry(scenario_type=ScenarioType.BUDGET, budget_version_id=UUID(int=9))
    assert created.budget_version_id == UUID(int=9)
