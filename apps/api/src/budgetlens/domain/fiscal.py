from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from budgetlens.domain.errors import ValidationError


def validate_fiscal_year_start_month(value: int) -> int:
    if value < 1 or value > 12:
        raise ValidationError(
            "INVALID_FISCAL_MONTH",
            "El mes de inicio fiscal debe estar entre 1 y 12.",
            field_errors=[
                {
                    "field": "fiscal_year_start_month",
                    "code": "INVALID_FISCAL_MONTH",
                    "message": "El mes de inicio fiscal debe estar entre 1 y 12.",
                }
            ],
        )
    return value


def fiscal_year_for_date(value: date, fiscal_year_start_month: int) -> int:
    start_month = validate_fiscal_year_start_month(fiscal_year_start_month)
    if start_month == 1:
        return value.year
    if value.month >= start_month:
        return value.year + 1
    return value.year


def fiscal_year_period_bounds(fiscal_year: int, fiscal_year_start_month: int) -> tuple[date, date]:
    start_month = validate_fiscal_year_start_month(fiscal_year_start_month)
    if start_month == 1:
        return date(fiscal_year, 1, 1), date(fiscal_year, 12, 1)
    return date(fiscal_year - 1, start_month, 1), date(fiscal_year, start_month - 1, 1)


@dataclass(frozen=True, slots=True)
class FiscalPeriod:
    period_start: date
    fiscal_year: int
    fiscal_year_start_month: int

    def __post_init__(self) -> None:
        validate_fiscal_year_start_month(self.fiscal_year_start_month)
        if self.period_start.day != 1:
            raise ValidationError(
                "INVALID_PERIOD",
                "El periodo debe iniciar el primer día del mes.",
                field_errors=[
                    {
                        "field": "period_start",
                        "code": "INVALID_PERIOD",
                        "message": "El periodo debe iniciar el primer día del mes.",
                    }
                ],
            )
        expected = fiscal_year_for_date(self.period_start, self.fiscal_year_start_month)
        if self.fiscal_year != expected:
            raise ValidationError(
                "INVALID_FISCAL_YEAR",
                "El año fiscal no coincide con el periodo.",
                field_errors=[
                    {
                        "field": "fiscal_year",
                        "code": "INVALID_FISCAL_YEAR",
                        "message": "El año fiscal no coincide con el periodo.",
                    }
                ],
            )

    @classmethod
    def from_date(cls, value: date, fiscal_year_start_month: int) -> FiscalPeriod:
        period_start = date(value.year, value.month, 1)
        return cls(
            period_start=period_start,
            fiscal_year=fiscal_year_for_date(period_start, fiscal_year_start_month),
            fiscal_year_start_month=fiscal_year_start_month,
        )

    def as_text(self) -> str:
        return self.period_start.isoformat()
