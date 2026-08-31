from __future__ import annotations

from datetime import date

import pytest

from budgetlens.domain.errors import ValidationError
from budgetlens.domain.fiscal import FiscalPeriod, fiscal_year_for_date, fiscal_year_period_bounds


def test_january_fiscal_year_matches_calendar_year() -> None:
    period = FiscalPeriod.from_date(date(2026, 6, 15), 1)
    assert period.period_start == date(2026, 6, 1)
    assert period.fiscal_year == 2026
    assert fiscal_year_period_bounds(2026, 1) == (date(2026, 1, 1), date(2026, 12, 1))


def test_april_fiscal_year_uses_ending_year() -> None:
    before_start = FiscalPeriod.from_date(date(2026, 3, 20), 4)
    after_start = FiscalPeriod.from_date(date(2026, 4, 2), 4)
    assert before_start.period_start == date(2026, 3, 1)
    assert before_start.fiscal_year == 2026
    assert after_start.period_start == date(2026, 4, 1)
    assert after_start.fiscal_year == 2027
    assert fiscal_year_period_bounds(2026, 4) == (date(2025, 4, 1), date(2026, 3, 1))


def test_date_belongs_to_exactly_one_period() -> None:
    first = FiscalPeriod.from_date(date(2026, 1, 1), 1)
    last = FiscalPeriod.from_date(date(2026, 1, 31), 1)
    assert first.period_start == last.period_start
    assert first.fiscal_year == last.fiscal_year == 2026


def test_invalid_start_month_is_rejected() -> None:
    with pytest.raises(ValidationError) as exc:
        fiscal_year_for_date(date(2026, 1, 1), 13)
    assert exc.value.code == "INVALID_FISCAL_MONTH"


def test_period_must_be_first_of_month() -> None:
    with pytest.raises(ValidationError):
        FiscalPeriod(period_start=date(2026, 1, 15), fiscal_year=2026, fiscal_year_start_month=1)
