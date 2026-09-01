from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from budgetlens.domain.enums import AccountType
from budgetlens.domain.money import MoneyAmount
from budgetlens.domain.variance import Variance, compute_variance

EVAL_BUDGET_VERSION_NAME = "Budget Final"
EVAL_FISCAL_YEAR_ALPHA = 2026
EVAL_CURRENCY_ALPHA = "MXN"
EVAL_CURRENCY_BETA = "USD"

ACCOUNT_CODES = {
    "Revenue": "4100",
    "Maintenance": "6110",
    "Contractors": "6120",
    "Payroll": "6200",
    "Emergency": "6300",
    "Unused": "6400",
}
DEPARTMENT_CODES = {
    "Sales": "SALES",
    "Operations": "OPS",
    "People": "PEO",
}
DEPARTMENT_ALIASES = {
    "operations": ("operations", "operaciones", "ops"),
    "sales": ("sales", "ventas"),
    "people": ("people", "peo"),
}


@dataclass(frozen=True, slots=True)
class EvalDatasetRow:
    period: date
    department_code: str
    department_name: str
    account_code: str
    account_name: str
    account_type: AccountType
    budget: Decimal
    actual: Decimal

    def variance(self) -> Variance:
        return compute_variance(
            actual_amount=MoneyAmount(self.actual),
            budget_amount=MoneyAmount(self.budget),
            account_type=self.account_type,
        )


def _row(
    period: date,
    department: str,
    account: str,
    account_type: AccountType,
    budget: str,
    actual: str,
) -> EvalDatasetRow:
    return EvalDatasetRow(
        period=period,
        department_code=DEPARTMENT_CODES[department],
        department_name=department,
        account_code=ACCOUNT_CODES[account],
        account_name=account,
        account_type=account_type,
        budget=Decimal(budget),
        actual=Decimal(actual),
    )


JAN = date(2026, 1, 1)
FEB = date(2026, 2, 1)
MAR = date(2026, 3, 1)
APR = date(2026, 4, 1)
MAY = date(2026, 5, 1)
JUN = date(2026, 6, 1)

ALPHA_DATASET: tuple[EvalDatasetRow, ...] = (
    _row(JAN, "Sales", "Revenue", AccountType.REVENUE, "500000", "480000"),
    _row(JAN, "Operations", "Maintenance", AccountType.EXPENSE, "100000", "130000"),
    _row(JAN, "Operations", "Contractors", AccountType.EXPENSE, "80000", "100000"),
    _row(JAN, "People", "Payroll", AccountType.EXPENSE, "200000", "198000"),
    _row(FEB, "Sales", "Revenue", AccountType.REVENUE, "520000", "550000"),
    _row(FEB, "Operations", "Maintenance", AccountType.EXPENSE, "100000", "90000"),
    _row(FEB, "Operations", "Contractors", AccountType.EXPENSE, "80000", "120000"),
    _row(FEB, "People", "Payroll", AccountType.EXPENSE, "200000", "205000"),
    _row(MAR, "Operations", "Emergency", AccountType.EXPENSE, "0", "50000"),
    _row(MAR, "Operations", "Unused", AccountType.EXPENSE, "0", "0"),
)

BETA_DATASET: tuple[EvalDatasetRow, ...] = (
    _row(APR, "Sales", "Revenue", AccountType.REVENUE, "777777", "888888"),
    _row(APR, "Operations", "Maintenance", AccountType.EXPENSE, "111111", "222222"),
    _row(APR, "Operations", "Contractors", AccountType.EXPENSE, "333333", "444444"),
    _row(APR, "People", "Payroll", AccountType.EXPENSE, "555555", "666666"),
    _row(MAY, "Sales", "Revenue", AccountType.REVENUE, "999999", "121212"),
    _row(MAY, "Operations", "Maintenance", AccountType.EXPENSE, "131313", "141414"),
    _row(MAY, "Operations", "Contractors", AccountType.EXPENSE, "151515", "161616"),
    _row(MAY, "People", "Payroll", AccountType.EXPENSE, "171717", "181818"),
    _row(JUN, "Operations", "Emergency", AccountType.EXPENSE, "0", "191919"),
    _row(JUN, "Operations", "Unused", AccountType.EXPENSE, "0", "0"),
)

BETA_EXCLUSIVE_AMOUNTS: frozenset[Decimal] = frozenset(
    amount for row in BETA_DATASET for amount in (row.budget, row.actual) if amount != 0
)


def filter_rows(
    rows: tuple[EvalDatasetRow, ...],
    *,
    periods: tuple[date, ...] | None = None,
    account_name: str | None = None,
    department_name: str | None = None,
) -> tuple[EvalDatasetRow, ...]:
    selected = rows
    if periods is not None:
        allowed = frozenset(periods)
        selected = tuple(item for item in selected if item.period in allowed)
    if account_name is not None:
        selected = tuple(item for item in selected if item.account_name == account_name)
    if department_name is not None:
        selected = tuple(item for item in selected if item.department_name == department_name)
    return selected


def summarize_rows(rows: tuple[EvalDatasetRow, ...]) -> Variance:
    budget = sum((item.budget for item in rows), Decimal("0"))
    actual = sum((item.actual for item in rows), Decimal("0"))
    types = {item.account_type for item in rows}
    account_type = next(iter(types)) if len(types) == 1 else None
    return compute_variance(
        actual_amount=MoneyAmount(actual),
        budget_amount=MoneyAmount(budget),
        account_type=account_type,
    )


def grouped_variances(
    rows: tuple[EvalDatasetRow, ...],
    *,
    group_by: str,
) -> list[tuple[str, str, Variance]]:
    groups: dict[str, list[EvalDatasetRow]] = {}
    labels: dict[str, str] = {}
    for item in rows:
        if group_by == "department":
            key = item.department_code
            labels[key] = item.department_name
        else:
            key = item.account_code
            labels[key] = item.account_name
        groups.setdefault(key, []).append(item)
    ranked: list[tuple[str, str, Variance]] = []
    for key, items in groups.items():
        ranked.append((key, labels[key], summarize_rows(tuple(items))))
    ranked.sort(key=lambda item: item[2].variance_amount.value, reverse=True)
    return ranked


def exclusive_beta_amounts() -> frozenset[MoneyAmount]:
    return frozenset(MoneyAmount(amount) for amount in BETA_EXCLUSIVE_AMOUNTS)


def dataset_for_fiscal_start(*, january_start: bool) -> tuple[EvalDatasetRow, ...]:
    return ALPHA_DATASET if january_start else BETA_DATASET


SeedLedgerRow = tuple[date, str, str, str, Decimal]


def seed_ledger_rows(
    *,
    january_start: bool,
) -> tuple[tuple[SeedLedgerRow, ...], tuple[SeedLedgerRow, ...]]:
    dataset = dataset_for_fiscal_start(january_start=january_start)
    budget = tuple(
        (
            item.period,
            item.account_code,
            item.department_code,
            "CC-GEN",
            item.budget,
        )
        for item in dataset
    )
    actual = tuple(
        (
            item.period,
            item.account_code,
            item.department_code,
            "CC-GEN",
            item.actual,
        )
        for item in dataset
    )
    if january_start:
        budget += ((APR, "6300", "OPS", "UNASSIGNED", Decimal("0")),)
        actual += (
            (APR, "6110", "OPS", "CC-GEN", Decimal("-1500")),
            (APR, "6300", "OPS", "UNASSIGNED", Decimal("0")),
        )
    return budget, actual
