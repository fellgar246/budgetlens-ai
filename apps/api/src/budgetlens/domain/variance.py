from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Decimal

from budgetlens.domain.enums import (
    PNL_ACCOUNT_TYPES,
    RATIO_SCALE,
    AccountType,
    Favorability,
    VarianceState,
)
from budgetlens.domain.money import MoneyAmount, parse_decimal

RATIO_QUANT = Decimal("1").scaleb(-RATIO_SCALE)


@dataclass(frozen=True, slots=True)
class Variance:
    actual_amount: MoneyAmount
    budget_amount: MoneyAmount
    variance_amount: MoneyAmount
    variance_percent: Decimal | None
    variance_state: VarianceState
    favorability: Favorability

    def percent_as_text(self) -> str | None:
        if self.variance_percent is None:
            return None
        return f"{self.variance_percent:.{RATIO_SCALE}f}"


def classify_favorability(
    variance_amount: MoneyAmount,
    account_type: AccountType | None,
) -> Favorability:
    if variance_amount.is_zero():
        return Favorability.NEUTRAL
    if account_type is AccountType.REVENUE:
        return Favorability.FAVORABLE if variance_amount.is_positive() else Favorability.UNFAVORABLE
    if account_type is AccountType.EXPENSE:
        return Favorability.UNFAVORABLE if variance_amount.is_positive() else Favorability.FAVORABLE
    return Favorability.UNKNOWN


def favorability_for_account_types(
    variance_amount: MoneyAmount,
    account_types: Iterable[AccountType],
) -> Favorability:
    types = frozenset(account_types)
    if variance_amount.is_zero():
        return Favorability.NEUTRAL
    if len(types) == 1:
        only = next(iter(types))
        return classify_favorability(variance_amount, only)
    return Favorability.UNKNOWN


def is_pnl_account_type(account_type: AccountType) -> bool:
    return account_type in PNL_ACCOUNT_TYPES


def compute_variance(
    *,
    actual_amount: MoneyAmount,
    budget_amount: MoneyAmount,
    account_type: AccountType | None = None,
) -> Variance:
    variance_amount = actual_amount - budget_amount
    if budget_amount.is_zero() and actual_amount.is_zero():
        percent: Decimal | None = None
        state = VarianceState.NO_ACTIVITY
    elif budget_amount.is_zero():
        percent = None
        state = VarianceState.UNBOUNDED
    else:
        raw = variance_amount.value / abs(budget_amount.value)
        if not raw.is_finite():
            percent = None
            state = VarianceState.UNBOUNDED
        else:
            percent = raw.quantize(RATIO_QUANT, rounding=ROUND_HALF_EVEN)
            state = VarianceState.DEFINED
    return Variance(
        actual_amount=actual_amount,
        budget_amount=budget_amount,
        variance_amount=variance_amount,
        variance_percent=percent,
        variance_state=state,
        favorability=classify_favorability(variance_amount, account_type),
    )


def parse_ratio(value: Decimal | str | int, *, field: str = "value") -> Decimal:
    parsed = parse_decimal(value, field=field)
    return parsed.quantize(RATIO_QUANT, rounding=ROUND_HALF_EVEN)
