from __future__ import annotations

from budgetlens.domain.enums import AccountType, Favorability, VarianceState
from budgetlens.domain.money import MoneyAmount
from budgetlens.domain.variance import compute_variance, favorability_for_account_types


def test_positive_budget_variance_amount() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("120"),
        budget_amount=MoneyAmount("100"),
        account_type=AccountType.EXPENSE,
    )
    assert result.variance_amount.as_text() == "20.0000"
    assert result.variance_percent is not None
    assert result.percent_as_text() == "0.200000"
    assert result.variance_state is VarianceState.DEFINED


def test_negative_budget_uses_absolute_denominator() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("-80"),
        budget_amount=MoneyAmount("-100"),
        account_type=AccountType.EXPENSE,
    )
    assert result.variance_amount.as_text() == "20.0000"
    assert result.percent_as_text() == "0.200000"


def test_zero_budget_and_zero_actual_is_no_activity() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("0"),
        budget_amount=MoneyAmount("0"),
        account_type=AccountType.REVENUE,
    )
    assert result.variance_amount.is_zero()
    assert result.variance_percent is None
    assert result.variance_state is VarianceState.NO_ACTIVITY
    assert result.favorability is Favorability.NEUTRAL


def test_zero_budget_nonzero_actual_is_unbounded() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("25"),
        budget_amount=MoneyAmount("0"),
        account_type=AccountType.EXPENSE,
    )
    assert result.variance_amount.as_text() == "25.0000"
    assert result.variance_percent is None
    assert result.variance_state is VarianceState.UNBOUNDED
    assert result.percent_as_text() is None


def test_expense_over_budget_is_unfavorable() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("120"),
        budget_amount=MoneyAmount("100"),
        account_type=AccountType.EXPENSE,
    )
    assert result.variance_amount.as_text() == "20.0000"
    assert result.favorability is Favorability.UNFAVORABLE


def test_expense_under_budget_is_favorable() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("80"),
        budget_amount=MoneyAmount("100"),
        account_type=AccountType.EXPENSE,
    )
    assert result.favorability is Favorability.FAVORABLE


def test_revenue_over_budget_is_favorable() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("120"),
        budget_amount=MoneyAmount("100"),
        account_type=AccountType.REVENUE,
    )
    assert result.variance_amount.as_text() == "20.0000"
    assert result.favorability is Favorability.FAVORABLE


def test_revenue_under_budget_is_unfavorable() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("80"),
        budget_amount=MoneyAmount("100"),
        account_type=AccountType.REVENUE,
    )
    assert result.favorability is Favorability.UNFAVORABLE


def test_other_account_without_policy_is_unknown() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("120"),
        budget_amount=MoneyAmount("100"),
        account_type=AccountType.ASSET,
    )
    assert result.favorability is Favorability.UNKNOWN


def test_zero_variance_is_neutral_for_other_types() -> None:
    result = compute_variance(
        actual_amount=MoneyAmount("50"),
        budget_amount=MoneyAmount("50"),
        account_type=AccountType.LIABILITY,
    )
    assert result.favorability is Favorability.NEUTRAL


def test_mixed_account_types_do_not_sum_row_labels() -> None:
    amount = MoneyAmount("20")
    assert (
        favorability_for_account_types(amount, [AccountType.REVENUE, AccountType.EXPENSE])
        is Favorability.UNKNOWN
    )
    assert favorability_for_account_types(
        MoneyAmount("0"), [AccountType.REVENUE, AccountType.EXPENSE]
    ) is (Favorability.NEUTRAL)
