from __future__ import annotations

from decimal import ROUND_HALF_EVEN, Decimal

from budgetlens.domain.enums import MONEY_SCALE
from budgetlens.domain.errors import ValidationError, field_issue

MONEY_QUANT = Decimal("1").scaleb(-MONEY_SCALE)
MONEY_MAX = Decimal("999999999999999.9999")
MONEY_MIN = -MONEY_MAX


def _reject_float(value: object) -> None:
    if type(value) is float:
        raise TypeError("money amounts cannot be constructed from float")


def parse_decimal(value: Decimal | str | int, *, field: str) -> Decimal:
    _reject_float(value)
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, int):
        parsed = Decimal(value)
    elif type(value) is str:
        cleaned = value.strip()
        if not cleaned:
            raise ValidationError(
                "INVALID_AMOUNT",
                "El importe no es válido.",
                field_errors=[field_issue(field, "INVALID_AMOUNT", "El importe no es válido.")],
            )
        try:
            parsed = Decimal(cleaned)
        except Exception as exc:
            raise ValidationError(
                "INVALID_AMOUNT",
                "El importe no es válido.",
                field_errors=[field_issue(field, "INVALID_AMOUNT", "El importe no es válido.")],
            ) from exc
    else:
        raise TypeError(f"unsupported amount type: {type(value).__name__}")
    if not parsed.is_finite():
        raise ValidationError(
            "INVALID_AMOUNT",
            "El importe no puede ser infinito ni indefinido.",
            field_errors=[
                {
                    "field": field,
                    "code": "INVALID_AMOUNT",
                    "message": "El importe no puede ser infinito ni indefinido.",
                }
            ],
        )
    return parsed


class MoneyAmount:
    __slots__ = ("_value",)

    def __init__(self, value: Decimal | str | int) -> None:
        parsed = parse_decimal(value, field="amount")
        quantized = parsed.quantize(MONEY_QUANT, rounding=ROUND_HALF_EVEN)
        if quantized < MONEY_MIN or quantized > MONEY_MAX:
            raise ValidationError(
                "AMOUNT_OUT_OF_RANGE",
                "El importe excede el rango permitido.",
                field_errors=[
                    {
                        "field": "amount",
                        "code": "AMOUNT_OUT_OF_RANGE",
                        "message": "El importe excede el rango permitido.",
                    }
                ],
            )
        self._value = quantized

    @property
    def value(self) -> Decimal:
        return self._value

    def is_zero(self) -> bool:
        return self._value == 0

    def is_positive(self) -> bool:
        return self._value > 0

    def is_negative(self) -> bool:
        return self._value < 0

    def __add__(self, other: object) -> MoneyAmount:
        if not isinstance(other, MoneyAmount):
            return NotImplemented
        return MoneyAmount(self._value + other._value)

    def __sub__(self, other: object) -> MoneyAmount:
        if not isinstance(other, MoneyAmount):
            return NotImplemented
        return MoneyAmount(self._value - other._value)

    def __abs__(self) -> MoneyAmount:
        return MoneyAmount(abs(self._value))

    def apply_percentage(self, ratio: Decimal | str | int) -> MoneyAmount:
        parsed = parse_decimal(ratio, field="value")
        return MoneyAmount(self._value * (Decimal(1) + parsed))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MoneyAmount):
            return NotImplemented
        return self._value == other._value

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, MoneyAmount):
            return NotImplemented
        return self._value < other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def as_text(self) -> str:
        return f"{self._value:.{MONEY_SCALE}f}"

    def __repr__(self) -> str:
        return f"MoneyAmount({self.as_text()!r})"


class Currency:
    __slots__ = ("_code",)

    def __init__(self, code: str) -> None:
        cleaned = code.strip().upper()
        if len(cleaned) != 3 or not cleaned.isalpha() or not cleaned.isascii():
            raise ValidationError(
                "INVALID_CURRENCY",
                "La moneda debe ser un código de tres letras.",
                field_errors=[
                    {
                        "field": "functional_currency",
                        "code": "INVALID_CURRENCY",
                        "message": "La moneda debe ser un código de tres letras.",
                    }
                ],
            )
        self._code = cleaned

    @property
    def code(self) -> str:
        return self._code

    def matches(self, other: Currency | str) -> bool:
        if isinstance(other, Currency):
            return self._code == other._code
        return self._code == Currency(other)._code

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Currency):
            return NotImplemented
        return self._code == other._code

    def __hash__(self) -> int:
        return hash(self._code)

    def __str__(self) -> str:
        return self._code

    def __repr__(self) -> str:
        return f"Currency({self._code!r})"


def reject_foreign_currency(*, row_currency: str, functional: Currency) -> None:
    incoming = Currency(row_currency)
    if not incoming.matches(functional):
        raise ValidationError(
            "CURRENCY_MISMATCH",
            "La moneda de la fila no coincide con la moneda funcional.",
            field_errors=[
                {
                    "field": "currency",
                    "code": "CURRENCY_MISMATCH",
                    "message": "La moneda de la fila no coincide con la moneda funcional.",
                }
            ],
        )
