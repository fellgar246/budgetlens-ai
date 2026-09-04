from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from budgetlens.domain.enums import ScenarioOperation
from budgetlens.domain.money import MoneyAmount
from budgetlens.domain.scenario import ScenarioRule, ScenarioScope, apply_scenario_rules


def test_zero_percent_and_empty_rules_equal_baseline() -> None:
    scope = ScenarioScope(
        period_from=date(2026, 1, 1),
        period_to=date(2026, 3, 1),
        account_ids=(),
        department_ids=(),
        cost_center_ids=(),
    )
    created = datetime(2026, 1, 1, tzinfo=UTC)
    empty = apply_scenario_rules(MoneyAmount("250"), [], created_at=created)
    assert empty.result.as_text() == "250.0000"
    zero = apply_scenario_rules(
        MoneyAmount("250"),
        [
            ScenarioRule(
                sequence=1,
                operation=ScenarioOperation.PERCENTAGE_CHANGE,
                value=Decimal("0"),
                scope=scope,
            )
        ],
        created_at=created,
    )
    assert zero.result.as_text() == "250.0000"


def test_overlapping_rules_apply_in_explicit_order() -> None:
    scope = ScenarioScope(
        period_from=date(2026, 7, 1),
        period_to=date(2026, 12, 1),
        account_ids=(),
        department_ids=(),
        cost_center_ids=(),
    )
    outcome = apply_scenario_rules(
        MoneyAmount("100"),
        [
            ScenarioRule(
                sequence=2,
                operation=ScenarioOperation.ABSOLUTE_CHANGE,
                value=Decimal("10"),
                scope=scope,
            ),
            ScenarioRule(
                sequence=1,
                operation=ScenarioOperation.PERCENTAGE_CHANGE,
                value=Decimal("0.0500"),
                scope=scope,
            ),
        ],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert outcome.result.as_text() == "115.0000"
    assert [step.sequence for step in outcome.breakdown] == [1, 2]
    assert outcome.breakdown[0].amount_after.as_text() == "105.0000"
    assert outcome.breakdown[1].amount_before.as_text() == "105.0000"


def test_scenario_does_not_share_identity_with_baseline() -> None:
    baseline = MoneyAmount("200")
    scope = ScenarioScope(
        period_from=date(2026, 1, 1),
        period_to=date(2026, 1, 1),
        account_ids=(UUID(int=1),),
        department_ids=(),
        cost_center_ids=(),
    )
    outcome = apply_scenario_rules(
        baseline,
        [
            ScenarioRule(
                sequence=1,
                operation=ScenarioOperation.PERCENTAGE_CHANGE,
                value=Decimal("0.1000"),
                scope=scope,
            )
        ],
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert baseline.as_text() == "200.0000"
    assert outcome.result.as_text() == "220.0000"
