from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from budgetlens.domain.money import Currency, MoneyAmount


@dataclass(frozen=True, slots=True)
class Evidence:
    tool_name: str
    authorized: bool
    period_from: date
    period_to: date
    budget_version_id: UUID
    currency: Currency
    figures: tuple[MoneyAmount, ...]


@dataclass(frozen=True, slots=True)
class GroundingDecision:
    can_conclude: bool
    period_from: date | None
    period_to: date | None
    budget_version_id: UUID | None
    currency: Currency | None


def evaluate_grounding(evidence: Sequence[Evidence]) -> GroundingDecision:
    if not evidence or not all(item.authorized and item.figures for item in evidence):
        return GroundingDecision(
            can_conclude=False,
            period_from=None,
            period_to=None,
            budget_version_id=None,
            currency=None,
        )
    first = evidence[0]
    return GroundingDecision(
        can_conclude=True,
        period_from=first.period_from,
        period_to=first.period_to,
        budget_version_id=first.budget_version_id,
        currency=first.currency,
    )


def conversation_may_mutate() -> bool:
    return False


def dimension_label_as_data(value: str) -> str:
    return value
