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


def test_money_parses_int_and_rejects_empty_or_unknown_types() -> None:
    assert MoneyAmount(12).as_text() == "12.0000"
    with pytest.raises(ValidationError) as empty:
        MoneyAmount("   ")
    assert empty.value.code == "INVALID_AMOUNT"
    with pytest.raises(ValidationError) as invalid:
        MoneyAmount("12,00")
    assert invalid.value.code == "INVALID_AMOUNT"
    with pytest.raises(TypeError, match="unsupported"):
        MoneyAmount(None)  # type: ignore[arg-type]


def test_money_arithmetic_and_comparisons() -> None:
    left = MoneyAmount("-2.5")
    right = MoneyAmount("1.5")
    assert left.is_negative()
    assert (left + right).as_text() == "-1.0000"
    assert (right - left).as_text() == "4.0000"
    assert abs(left).as_text() == "2.5000"
    assert left.apply_percentage("0.1000").as_text() == "-2.7500"
    assert left < right
    assert left != right
    assert hash(left) == hash(MoneyAmount("-2.5000"))
    assert left.__add__(1) is NotImplemented
    assert left.__sub__(1) is NotImplemented
    assert left.__eq__(1) is NotImplemented
    assert left.__lt__(1) is NotImplemented
    assert "MoneyAmount" in repr(left)


def test_currency_matches_and_equality() -> None:
    mxn = Currency("MXN")
    assert mxn.matches("mxn")
    assert mxn.matches(Currency("MXN"))
    assert mxn == Currency("MXN")
    assert mxn.__eq__("MXN") is NotImplemented
    assert hash(mxn) == hash(Currency("mxn"))
    assert str(mxn) == "MXN"
    assert "Currency" in repr(mxn)
