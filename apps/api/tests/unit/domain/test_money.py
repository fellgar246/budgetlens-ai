from __future__ import annotations

from decimal import Decimal

import pytest

from budgetlens.domain.errors import ValidationError
from budgetlens.domain.money import Currency, MoneyAmount, reject_foreign_currency


def test_money_quantizes_to_four_decimals() -> None:
    amount = MoneyAmount("10.12345")
    assert amount.as_text() == "10.1234"
    assert amount.value == Decimal("10.1234")


def test_money_accepts_large_values() -> None:
    amount = MoneyAmount("9999999999999.1234")
    assert amount.as_text() == "9999999999999.1234"


def test_money_rejects_float() -> None:
    with pytest.raises(TypeError, match="float"):
        MoneyAmount(1.25)  # type: ignore[arg-type]


def test_money_rejects_nan_and_infinity() -> None:
    with pytest.raises(ValidationError) as nan_error:
        MoneyAmount("NaN")
    assert nan_error.value.code == "INVALID_AMOUNT"
    with pytest.raises(ValidationError) as inf_error:
        MoneyAmount("Infinity")
    assert inf_error.value.code == "INVALID_AMOUNT"


def test_money_rejects_out_of_range() -> None:
    with pytest.raises(ValidationError) as exc:
        MoneyAmount("1000000000000000")
    assert exc.value.code == "AMOUNT_OUT_OF_RANGE"


def test_currency_normalizes_iso_code() -> None:
    assert Currency("mxn").code == "MXN"


def test_currency_rejects_invalid_code() -> None:
    with pytest.raises(ValidationError) as exc:
        Currency("MX")
    assert exc.value.code == "INVALID_CURRENCY"


def test_foreign_currency_is_rejected_by_row() -> None:
    with pytest.raises(ValidationError) as exc:
        reject_foreign_currency(row_currency="USD", functional=Currency("MXN"))
    assert exc.value.code == "CURRENCY_MISMATCH"
