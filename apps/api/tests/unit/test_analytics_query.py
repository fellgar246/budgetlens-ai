from __future__ import annotations

from datetime import date
from uuid import UUID

import pytest

from budgetlens.application.analytics_query import (
    BreakdownItem,
    build_variance_metrics,
    parse_analytics_query,
    sort_breakdown_items,
)
from budgetlens.domain.enums import AccountType, AnalyticsSort, SortDirection
from budgetlens.domain.errors import ValidationError
from budgetlens.domain.money import MoneyAmount


def test_query_rejects_non_month_start_and_inverted_range() -> None:
    with pytest.raises(ValidationError) as inverted:
        parse_analytics_query(
            fiscal_year=2027,
            period_from=date(2027, 3, 1),
            period_to=date(2027, 1, 1),
            budget_version_id=UUID(int=1),
        )
    assert inverted.value.code == "INVALID_PERIOD"
    with pytest.raises(ValidationError) as mid_month:
        parse_analytics_query(
            fiscal_year=2027,
            period_from=date(2027, 1, 15),
            period_to=date(2027, 2, 1),
            budget_version_id=UUID(int=1),
        )
    assert mid_month.value.code == "INVALID_PERIOD"


def test_mixed_totals_are_unknown_and_zero_budget_stays_null() -> None:
    mixed = build_variance_metrics(
        MoneyAmount("100"),
        MoneyAmount("130"),
        [AccountType.REVENUE, AccountType.EXPENSE],
    )
    assert mixed.favorability == "unknown"
    assert mixed.variance_amount.as_text() == "30.0000"
    unbounded = build_variance_metrics(MoneyAmount("0"), MoneyAmount("25"), [AccountType.EXPENSE])
    assert unbounded.variance_percent is None
    assert unbounded.variance_state == "unbounded"
    idle = build_variance_metrics(MoneyAmount("0"), MoneyAmount("0"), [AccountType.EXPENSE])
    assert idle.variance_percent is None
    assert idle.variance_state == "no_activity"


def test_sort_keeps_code_order_on_absolute_variance_ties() -> None:
    left = BreakdownItem(
        group_id="2",
        group_code="TIEB",
        group_name="Second",
        metrics=build_variance_metrics(MoneyAmount("10"), MoneyAmount("25"), [AccountType.EXPENSE]),
    )
    right = BreakdownItem(
        group_id="1",
        group_code="TIEA",
        group_name="First",
        metrics=build_variance_metrics(MoneyAmount("10"), MoneyAmount("25"), [AccountType.EXPENSE]),
    )
    ordered = sort_breakdown_items(
        [left, right], AnalyticsSort.ABSOLUTE_VARIANCE, SortDirection.DESC
    )
    assert [item.group_code for item in ordered] == ["TIEA", "TIEB"]
