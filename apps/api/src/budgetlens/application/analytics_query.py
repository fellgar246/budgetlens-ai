from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import cast
from uuid import UUID

from budgetlens.domain.enums import AccountType, AnalyticsSort, SortDirection
from budgetlens.domain.errors import ValidationError, field_issue
from budgetlens.domain.money import MoneyAmount
from budgetlens.domain.variance import compute_variance, favorability_for_account_types


@dataclass(frozen=True, slots=True)
class AnalyticsQuery:
    fiscal_year: int
    period_from: date
    period_to: date
    budget_version_id: UUID
    account_ids: tuple[UUID, ...]
    department_ids: tuple[UUID, ...]
    cost_center_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        if self.period_from.day != 1 or self.period_to.day != 1:
            raise ValidationError(
                "INVALID_PERIOD",
                "El periodo debe usar el primer día de cada mes.",
                field_errors=[field_issue("period_from", "INVALID_PERIOD", "Usa YYYY-MM-01.")],
            )
        if self.period_to < self.period_from:
            raise ValidationError(
                "INVALID_PERIOD",
                "El periodo final no puede ser anterior al inicial.",
            )


@dataclass(frozen=True, slots=True)
class VarianceMetrics:
    budget_amount: MoneyAmount
    actual_amount: MoneyAmount
    variance_amount: MoneyAmount
    variance_percent: str | None
    variance_state: str
    favorability: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "budget_amount": self.budget_amount.as_text(),
            "actual_amount": self.actual_amount.as_text(),
            "variance_amount": self.variance_amount.as_text(),
            "variance_percent": self.variance_percent,
            "variance_state": self.variance_state,
            "favorability": self.favorability,
        }


@dataclass(frozen=True, slots=True)
class BreakdownItem:
    group_id: str
    group_code: str
    group_name: str
    metrics: VarianceMetrics


@dataclass(frozen=True, slots=True)
class VarianceSummary:
    query: AnalyticsQuery
    currency: str
    metrics: VarianceMetrics


def parse_analytics_query(
    *,
    fiscal_year: int,
    period_from: date,
    period_to: date,
    budget_version_id: UUID,
    account_ids: list[UUID] | None = None,
    department_ids: list[UUID] | None = None,
    cost_center_ids: list[UUID] | None = None,
) -> AnalyticsQuery:
    return AnalyticsQuery(
        fiscal_year=fiscal_year,
        period_from=period_from,
        period_to=period_to,
        budget_version_id=budget_version_id,
        account_ids=tuple(account_ids or ()),
        department_ids=tuple(department_ids or ()),
        cost_center_ids=tuple(cost_center_ids or ()),
    )


def build_variance_metrics(
    budget: MoneyAmount, actual: MoneyAmount, types: list[AccountType]
) -> VarianceMetrics:
    account_type = types[0] if len(types) == 1 else None
    computed = compute_variance(
        actual_amount=actual, budget_amount=budget, account_type=account_type
    )
    favorability = favorability_for_account_types(computed.variance_amount, types)
    return VarianceMetrics(
        budget_amount=computed.budget_amount,
        actual_amount=computed.actual_amount,
        variance_amount=computed.variance_amount,
        variance_percent=computed.percent_as_text(),
        variance_state=computed.variance_state.value,
        favorability=favorability.value,
    )


def sort_breakdown_items(
    items: list[BreakdownItem], sort: AnalyticsSort, direction: SortDirection
) -> list[BreakdownItem]:
    reverse = direction is SortDirection.DESC

    def key(item: BreakdownItem) -> tuple[Decimal, str, str]:
        metrics = item.metrics
        if sort is AnalyticsSort.BUDGET_AMOUNT:
            primary = metrics.budget_amount.value
        elif sort is AnalyticsSort.ACTUAL_AMOUNT:
            primary = metrics.actual_amount.value
        elif sort is AnalyticsSort.ABSOLUTE_VARIANCE:
            primary = abs(metrics.variance_amount.value)
        else:
            primary = metrics.variance_amount.value
        if reverse:
            primary = -primary
        return (primary, item.group_code, item.group_id)

    return sorted(items, key=key)


def parse_account_types(value: object) -> list[AccountType]:
    if value is None:
        return []
    if isinstance(value, list):
        raw = cast(list[object], value)
        return [AccountType(str(item)) for item in raw if item]
    if isinstance(value, tuple):
        raw_tuple = cast(tuple[object, ...], value)
        return [AccountType(str(item)) for item in raw_tuple if item]
    if isinstance(value, set):
        raw_set = cast(set[object], value)
        return [AccountType(str(item)) for item in raw_set if item]
    parts = {item for item in str(value).split(",") if item}
    return [AccountType(item) for item in parts]
