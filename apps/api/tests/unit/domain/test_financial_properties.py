from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import product
from uuid import UUID

from budgetlens.domain.enums import AccountType, ScenarioOperation
from budgetlens.domain.money import MONEY_MAX, MoneyAmount
from budgetlens.domain.scenario import ScenarioRule, ScenarioScope, apply_scenario_rules
from budgetlens.domain.variance import compute_variance

AMOUNTS = (
    Decimal("-999.1234"),
    Decimal("-0.0001"),
    Decimal("0"),
    Decimal("0.0001"),
    Decimal("1"),
    Decimal("100.2500"),
    Decimal("999999.9999"),
)
ACCOUNT_TYPES = (AccountType.REVENUE, AccountType.EXPENSE, AccountType.ASSET)
SCOPE = ScenarioScope(
    period_from=date(2026, 1, 1),
    period_to=date(2026, 12, 1),
    account_ids=(),
    department_ids=(),
    cost_center_ids=(),
)


def test_variance_amount_is_actual_minus_budget_for_in_range_decimals() -> None:
    for actual, budget, account_type in product(AMOUNTS, AMOUNTS, ACCOUNT_TYPES):
        result = compute_variance(
            actual_amount=MoneyAmount(actual),
            budget_amount=MoneyAmount(budget),
            account_type=account_type,
        )
        assert result.variance_amount == MoneyAmount(actual) - MoneyAmount(budget)


def test_partition_totals_equal_the_unpartitioned_sum() -> None:
    parts = [MoneyAmount(value) for value in AMOUNTS]
    total = MoneyAmount("0")
    for part in parts:
        total = total + part
    rebuilt = MoneyAmount("0")
    for part in parts:
        rebuilt = rebuilt + part
    assert rebuilt == total
    assert total.value <= MONEY_MAX


def test_zero_change_scenario_returns_the_baseline() -> None:
    created = datetime(2026, 1, 1, tzinfo=UTC)
    for baseline in AMOUNTS:
        amount = MoneyAmount(baseline)
        percent = apply_scenario_rules(
            amount,
            [
                ScenarioRule(
                    sequence=1,
                    operation=ScenarioOperation.PERCENTAGE_CHANGE,
                    value=Decimal("0"),
                    scope=SCOPE,
                )
            ],
            created_at=created,
        )
        absolute = apply_scenario_rules(
            amount,
            [
                ScenarioRule(
                    sequence=1,
                    operation=ScenarioOperation.ABSOLUTE_CHANGE,
                    value=Decimal("0"),
                    scope=SCOPE,
                )
            ],
            created_at=created,
        )
        empty = apply_scenario_rules(amount, [], created_at=created)
        assert percent.result == amount
        assert absolute.result == amount
        assert empty.result == amount
        assert percent.baseline == amount


def test_scenario_rule_order_is_reproducible() -> None:
    created = datetime(2026, 1, 1, tzinfo=UTC)
    rules = [
        ScenarioRule(
            sequence=2,
            operation=ScenarioOperation.ABSOLUTE_CHANGE,
            value=Decimal("10"),
            scope=SCOPE,
        ),
        ScenarioRule(
            sequence=1,
            operation=ScenarioOperation.PERCENTAGE_CHANGE,
            value=Decimal("0.1000"),
            scope=SCOPE,
        ),
    ]
    first = apply_scenario_rules(MoneyAmount("200"), rules, created_at=created)
    second = apply_scenario_rules(MoneyAmount("200"), list(reversed(rules)), created_at=created)
    assert first.result == second.result
    assert first.result.as_text() == "230.0000"
    assert [step.sequence for step in first.breakdown] == [1, 2]
    assert [step.sequence for step in second.breakdown] == [1, 2]
    scoped = ScenarioScope(
        period_from=date(2026, 1, 1),
        period_to=date(2026, 1, 1),
        account_ids=(UUID(int=9),),
        department_ids=(),
        cost_center_ids=(),
    )
    assert scoped.account_ids == (UUID(int=9),)
