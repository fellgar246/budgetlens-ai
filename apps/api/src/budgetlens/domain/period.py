from __future__ import annotations

from datetime import date, datetime

from budgetlens.domain.errors import ValidationError, field_issue
from budgetlens.domain.fiscal import FiscalPeriod


def parse_period_start(value: str, *, field: str = "period") -> date:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError(
            "INVALID_PERIOD",
            "El periodo no es válido.",
            field_errors=[field_issue(field, "INVALID_PERIOD", "El periodo no es válido.")],
        )
    for fmt in ("%Y-%m-%d", "%Y-%m", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            parsed = datetime.strptime(cleaned, fmt).date()
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            continue
    raise ValidationError(
        "INVALID_PERIOD",
        "El periodo no es válido.",
        field_errors=[field_issue(field, "INVALID_PERIOD", "El periodo no es válido.")],
    )


def period_in_fiscal_year(
    period_start: date,
    *,
    fiscal_year: int,
    fiscal_year_start_month: int,
    field: str = "period",
) -> FiscalPeriod:
    period = FiscalPeriod.from_date(period_start, fiscal_year_start_month)
    if period.fiscal_year != fiscal_year:
        raise ValidationError(
            "INVALID_PERIOD",
            "El periodo está fuera del año fiscal.",
            field_errors=[
                field_issue(field, "INVALID_PERIOD", "El periodo está fuera del año fiscal.")
            ],
        )
    return period
