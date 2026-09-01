from __future__ import annotations

import pytest

from budgetlens.application.row_normalization import normalize_row, parse_mapped_amount
from budgetlens.domain.errors import ValidationError
from budgetlens.domain.importing import ParsedCellRow
from budgetlens.domain.money import Currency

MAPPING = {
    "period": "period",
    "account_code": "account_code",
    "department_code": "department_code",
    "cost_center_code": "cost_center_code",
    "amount": "amount",
    "currency": "currency",
}


def _row(values: dict[str, str], *, row_number: int = 2) -> ParsedCellRow:
    return ParsedCellRow(row_number=row_number, values=values, formula_fields=())


def test_leading_zeros_are_preserved_as_text() -> None:
    item, issues = normalize_row(
        _row(
            {
                "period": "2026-01",
                "account_code": "0610",
                "department_code": "OPS",
                "cost_center_code": "CC-GEN",
                "amount": "25.5000",
                "currency": "mxn",
            }
        ),
        mapping=MAPPING,
        amount_locale="en",
        functional=Currency("MXN"),
        fiscal_year=2026,
        fiscal_year_start_month=1,
    )
    assert item is not None
    assert item.account_code == "0610"
    assert item.currency == "MXN"
    assert item.period_start.isoformat() == "2026-01-01"
    assert not [issue for issue in issues if issue.severity.value == "error"]


def test_empty_cost_center_defaults_to_unassigned_warning() -> None:
    item, issues = normalize_row(
        _row(
            {
                "period": "2026-01-15",
                "account_code": "6100",
                "department_code": "OPS",
                "cost_center_code": "",
                "amount": "10.0000",
                "currency": "MXN",
            }
        ),
        mapping=MAPPING,
        amount_locale="en",
        functional=Currency("MXN"),
        fiscal_year=None,
        fiscal_year_start_month=1,
    )
    assert item is not None
    assert item.cost_center_code == "UNASSIGNED"
    assert any(issue.code == "EMPTY_OPTIONAL_VALUE" for issue in issues)


def test_locale_es_converts_decimal_explicitly() -> None:
    amount = parse_mapped_amount("1.250,50", locale="es")
    assert amount.as_text() == "1250.5000"
    with pytest.raises(ValidationError) as exc:
        parse_mapped_amount("1.250,50", locale="en")
    assert exc.value.code == "INVALID_AMOUNT"


def test_text_truncation_is_not_silent() -> None:
    item, issues = normalize_row(
        _row(
            {
                "period": "2026-01",
                "account_code": "6" * 65,
                "department_code": "OPS",
                "cost_center_code": "CC-GEN",
                "amount": "10.0000",
                "currency": "MXN",
            }
        ),
        mapping=MAPPING,
        amount_locale="en",
        functional=Currency("MXN"),
        fiscal_year=2026,
        fiscal_year_start_month=1,
    )
    assert item is None
    assert any(issue.code == "TEXT_TRUNCATION" for issue in issues)


def test_interleaved_empty_row_is_a_warning() -> None:
    item, issues = normalize_row(
        _row(
            {
                "period": "",
                "account_code": "",
                "department_code": "",
                "cost_center_code": "",
                "amount": "",
                "currency": "",
            }
        ),
        mapping=MAPPING,
        amount_locale="en",
        functional=Currency("MXN"),
        fiscal_year=2026,
        fiscal_year_start_month=1,
    )
    assert item is None
    assert issues[0].code == "EMPTY_OPTIONAL_VALUE"
    assert issues[0].severity.value == "warning"
