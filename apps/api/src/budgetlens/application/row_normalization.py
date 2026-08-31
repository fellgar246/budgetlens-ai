from __future__ import annotations

from decimal import Decimal

from budgetlens.domain.dimensions import normalize_code, resolve_cost_center_code
from budgetlens.domain.enums import UNASSIGNED_CODE, AccountType, ImportErrorSeverity
from budgetlens.domain.errors import ValidationError
from budgetlens.domain.importing import ImportIssue, NormalizedImportRow, ParsedCellRow
from budgetlens.domain.money import Currency, MoneyAmount, parse_decimal
from budgetlens.domain.period import parse_period_start, period_in_fiscal_year
from budgetlens.domain.text_safety import redact_cell


def parse_mapped_amount(value: str, *, locale: str) -> MoneyAmount:
    cleaned = value.strip()
    if locale == "es":
        cleaned = cleaned.replace(" ", "").replace(".", "").replace(",", ".")
    else:
        compact = cleaned.replace(" ", "")
        if "," in compact and "." in compact:
            cleaned = compact.replace(",", "")
        elif "," in compact and "." not in compact:
            raise ValidationError(
                "INVALID_AMOUNT",
                "El importe usa un separador ambiguo.",
            )
        else:
            cleaned = compact
    return MoneyAmount(parse_decimal(cleaned, field="amount"))


def mapped_value(row: ParsedCellRow, mapping: dict[str, str], field: str) -> str:
    header = mapping.get(field)
    if header is None:
        return ""
    return row.values.get(header, "")


def normalize_row(
    row: ParsedCellRow,
    *,
    mapping: dict[str, str],
    amount_locale: str,
    functional: Currency,
    fiscal_year: int | None,
    fiscal_year_start_month: int,
) -> tuple[NormalizedImportRow | None, list[ImportIssue]]:
    issues: list[ImportIssue] = []
    if row.formula_fields:
        for field in row.formula_fields:
            canonical = next((key for key, header in mapping.items() if header == field), field)
            issues.append(
                _issue(
                    row.row_number,
                    canonical,
                    "FORMULA_NOT_ALLOWED",
                    "No se permiten fórmulas en columnas mapeadas.",
                    mapped_value(row, mapping, canonical),
                )
            )
        return None, issues

    values = {field: mapped_value(row, mapping, field).strip() for field in mapping}
    if not any(values.values()):
        issues.append(
            _issue(
                row.row_number,
                "row",
                "EMPTY_OPTIONAL_VALUE",
                "La fila vacía se omitió.",
                "",
                ImportErrorSeverity.WARNING,
            )
        )
        return None, issues

    for field in ("period", "account_code", "department_code", "amount", "currency"):
        if not values.get(field):
            issues.append(
                _issue(row.row_number, field, "MISSING_COLUMN", "Falta un valor requerido.", "")
            )

    period_start = None
    fiscal = fiscal_year
    if values.get("period"):
        try:
            period_start = parse_period_start(values["period"])
            if fiscal_year is not None:
                period_in_fiscal_year(
                    period_start,
                    fiscal_year=fiscal_year,
                    fiscal_year_start_month=fiscal_year_start_month,
                )
                fiscal = fiscal_year
            else:
                from budgetlens.domain.fiscal import fiscal_year_for_date

                fiscal = fiscal_year_for_date(period_start, fiscal_year_start_month)
        except ValidationError as exc:
            issues.append(_issue(row.row_number, "period", exc.code, exc.message, values["period"]))

    amount = None
    if values.get("amount"):
        try:
            amount = parse_mapped_amount(values["amount"], locale=amount_locale)
        except (ValidationError, TypeError):
            issues.append(
                _issue(
                    row.row_number,
                    "amount",
                    "INVALID_AMOUNT",
                    "El importe no es válido.",
                    values["amount"],
                )
            )

    currency = None
    if values.get("currency"):
        try:
            currency = Currency(values["currency"])
            if not currency.matches(functional):
                issues.append(
                    _issue(
                        row.row_number,
                        "currency",
                        "INVALID_CURRENCY",
                        "La moneda no coincide con la moneda funcional.",
                        values["currency"],
                    )
                )
        except ValidationError:
            issues.append(
                _issue(
                    row.row_number,
                    "currency",
                    "INVALID_CURRENCY",
                    "La moneda no es un código válido.",
                    values["currency"],
                )
            )

    account_code = _bounded_code(
        values.get("account_code", ""), "account_code", issues, row.row_number
    )
    department_code = _bounded_code(
        values.get("department_code", ""), "department_code", issues, row.row_number
    )
    raw_cc = values.get("cost_center_code", "")
    warnings: list[ImportIssue] = []
    if not raw_cc.strip():
        cost_center_code = UNASSIGNED_CODE
        warnings.append(
            _issue(
                row.row_number,
                "cost_center_code",
                "EMPTY_OPTIONAL_VALUE",
                "Se aplicó Sin asignar al centro de costo vacío.",
                "",
                ImportErrorSeverity.WARNING,
            )
        )
    else:
        cost_center_code = _bounded_code(
            raw_cc, "cost_center_code", issues, row.row_number
        ) or resolve_cost_center_code(raw_cc)

    account_name = _bounded_text(
        values.get("account_name", ""), "account_name", 160, issues, row.row_number
    )
    department_name = _bounded_text(
        values.get("department_name", ""), "department_name", 160, issues, row.row_number
    )
    cost_center_name = _bounded_text(
        values.get("cost_center_name", ""), "cost_center_name", 160, issues, row.row_number
    )
    source_reference = _bounded_text(
        values.get("source_reference", ""), "source_reference", 160, issues, row.row_number
    )
    account_type = values.get("account_type", "").strip().lower() or None
    if account_type:
        try:
            AccountType(account_type)
        except ValueError:
            issues.append(
                _issue(
                    row.row_number,
                    "account_type",
                    "MISSING_COLUMN",
                    "El tipo de cuenta no es válido.",
                    account_type,
                )
            )
            account_type = None

    blocking = [item for item in issues if item.severity is ImportErrorSeverity.ERROR]
    if blocking or period_start is None or amount is None or currency is None or fiscal is None:
        return None, issues + warnings
    if not account_code or not department_code:
        return None, issues + warnings

    return (
        NormalizedImportRow(
            row_number=row.row_number,
            period_start=period_start,
            fiscal_year=fiscal,
            account_code=account_code,
            account_name=account_name,
            account_type=account_type,
            department_code=department_code,
            department_name=department_name,
            cost_center_code=cost_center_code or UNASSIGNED_CODE,
            cost_center_name=cost_center_name,
            amount=amount,
            currency=currency.code,
            source_reference=source_reference,
            warnings=tuple(warnings),
        ),
        issues + warnings,
    )


def _bounded_code(value: str, field: str, issues: list[ImportIssue], row_number: int) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > 64:
        issues.append(
            _issue(
                row_number,
                field,
                "TEXT_TRUNCATION",
                "El valor excede el límite permitido.",
                cleaned,
            )
        )
        return None
    try:
        return normalize_code(cleaned, field=field)
    except ValidationError as exc:
        issues.append(_issue(row_number, field, exc.code, exc.message, cleaned))
        return None


def _bounded_text(
    value: str, field: str, max_length: int, issues: list[ImportIssue], row_number: int
) -> str | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > max_length:
        issues.append(
            _issue(
                row_number,
                field,
                "TEXT_TRUNCATION",
                "El valor excede el límite permitido.",
                cleaned,
            )
        )
        return None
    return cleaned


def _issue(
    row_number: int,
    field: str,
    code: str,
    message: str,
    raw: str,
    severity: ImportErrorSeverity = ImportErrorSeverity.ERROR,
) -> ImportIssue:
    return ImportIssue(
        row_number=row_number,
        field=field,
        code=code,
        message=message,
        raw_value_redacted=redact_cell(raw),
        severity=severity,
    )


def zero_total() -> Decimal:
    return Decimal("0.0000")
