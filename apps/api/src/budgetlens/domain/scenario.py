from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from budgetlens.domain.enums import ScenarioOperation
from budgetlens.domain.errors import ValidationError
from budgetlens.domain.money import MoneyAmount
from budgetlens.domain.variance import parse_ratio


@dataclass(frozen=True, slots=True)
class ScenarioScope:
    period_from: date
    period_to: date
    account_ids: tuple[UUID, ...]
    department_ids: tuple[UUID, ...]
    cost_center_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        if self.period_from.day != 1 or self.period_to.day != 1:
            raise ValidationError(
                "INVALID_PERIOD",
                "El alcance del escenario debe usar el primer día de cada mes.",
            )
        if self.period_to < self.period_from:
            raise ValidationError(
                "INVALID_PERIOD",
                "El periodo final no puede ser anterior al inicial.",
            )


@dataclass(frozen=True, slots=True)
class ScenarioRule:
    sequence: int
    operation: ScenarioOperation
    value: Decimal
    scope: ScenarioScope


@dataclass(frozen=True, slots=True)
class ScenarioStep:
    sequence: int
    operation: ScenarioOperation
    value: Decimal
    amount_before: MoneyAmount
    amount_after: MoneyAmount


@dataclass(frozen=True, slots=True)
class ScenarioOutcome:
    baseline: MoneyAmount
    result: MoneyAmount
    breakdown: tuple[ScenarioStep, ...]
    created_at: datetime


def apply_scenario_rules(
    baseline: MoneyAmount,
    rules: Sequence[ScenarioRule],
    *,
    created_at: datetime,
) -> ScenarioOutcome:
    current = baseline
    steps: list[ScenarioStep] = []
    for rule in sorted(rules, key=lambda item: item.sequence):
        before = current
        if rule.operation is ScenarioOperation.PERCENTAGE_CHANGE:
            current = current.apply_percentage(parse_ratio(rule.value))
        elif rule.operation is ScenarioOperation.ABSOLUTE_CHANGE:
            current = current + MoneyAmount(rule.value)
        else:
            raise ValidationError("INVALID_OPERATION", "La operación del escenario no es válida.")
        steps.append(
            ScenarioStep(
                sequence=rule.sequence,
                operation=rule.operation,
                value=(
                    parse_ratio(rule.value)
                    if rule.operation is ScenarioOperation.PERCENTAGE_CHANGE
                    else MoneyAmount(rule.value).value
                ),
                amount_before=before,
                amount_after=current,
            )
        )
    return ScenarioOutcome(
        baseline=baseline,
        result=current,
        breakdown=tuple(steps),
        created_at=created_at,
    )
