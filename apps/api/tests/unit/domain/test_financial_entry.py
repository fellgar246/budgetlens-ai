from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

import pytest

from budgetlens.domain.enums import OrganizationStatus, ScenarioType
from budgetlens.domain.errors import ValidationError
from budgetlens.domain.financial_entry import FinancialEntry
from budgetlens.domain.money import Currency, MoneyAmount
from budgetlens.domain.organization import Organization


def _org() -> Organization:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return Organization(
        id=UUID(int=2),
        name="Alpha",
        slug="alpha",
        functional_currency=Currency("MXN"),
        fiscal_year_start_month=1,
        status=OrganizationStatus.ACTIVE,
        created_at=now,
        updated_at=now,
        version=1,
    )


def _entry(
    *,
    period_start: date = date(2026, 1, 1),
    scenario_type: ScenarioType = ScenarioType.ACTUAL,
    budget_version_id: UUID | None = None,
    currency: str = "MXN",
    fiscal_year: int = 2026,
    organization_id: UUID | None = None,
) -> FinancialEntry:
    return FinancialEntry(
        id=UUID(int=1),
        organization_id=UUID(int=2) if organization_id is None else organization_id,
        import_job_id=UUID(int=3),
        scenario_type=scenario_type,
        budget_version_id=budget_version_id,
        period_start=period_start,
        fiscal_year=fiscal_year,
        account_id=UUID(int=4),
        department_id=UUID(int=5),
        cost_center_id=UUID(int=6),
        amount=MoneyAmount("10"),
        currency=Currency(currency),
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


def test_entry_must_match_organization_currency_and_fiscal_year() -> None:
    organization = _org()
    _entry().assert_consistent_with(organization)
    with pytest.raises(ValidationError) as currency:
        _entry(currency="USD").assert_consistent_with(organization)
    assert currency.value.code == "CURRENCY_MISMATCH"
    with pytest.raises(ValidationError) as year:
        _entry(fiscal_year=2025).assert_consistent_with(organization)
    assert year.value.code == "INVALID_FISCAL_YEAR"
    with pytest.raises(ValidationError) as tenant:
        _entry(organization_id=UUID(int=99)).assert_consistent_with(organization)
    assert tenant.value.code == "TENANT_MISMATCH"
