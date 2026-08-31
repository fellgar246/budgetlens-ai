from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from typing import Any
from uuid import UUID

from budgetlens.domain.enums import ImportErrorSeverity, ImportJobStatus, ScenarioType
from budgetlens.domain.errors import ConflictError, ValidationError, field_issue
from budgetlens.domain.idempotency import import_idempotency_fingerprint
from budgetlens.domain.money import MoneyAmount

CANONICAL_FIELDS = (
    "period",
    "account_code",
    "account_name",
    "account_type",
    "department_code",
    "department_name",
    "cost_center_code",
    "cost_center_name",
    "amount",
    "currency",
    "source_reference",
)
REQUIRED_FIELDS = ("period", "account_code", "department_code", "amount", "currency")
NAME_ALIASES = {
    "period": ("period", "month", "periodo", "mes"),
    "account_code": ("account_code", "account", "cuenta"),
    "account_name": ("account_name", "account name"),
    "account_type": ("account_type", "type", "tipo"),
    "department_code": ("department_code", "department", "departamento"),
    "department_name": ("department_name", "department name"),
    "cost_center_code": ("cost_center_code", "cost center", "centro de costo", "cost_center"),
    "cost_center_name": ("cost_center_name", "cost center name"),
    "amount": ("amount", "actual", "budget", "importe", "monto"),
    "currency": ("currency", "moneda"),
    "source_reference": ("source_reference", "reference", "referencia"),
}
ALLOWED_TRANSITIONS: dict[ImportJobStatus, frozenset[ImportJobStatus]] = {
    ImportJobStatus.CREATED: frozenset({ImportJobStatus.UPLOADED, ImportJobStatus.CANCELLED}),
    ImportJobStatus.UPLOADED: frozenset(
        {
            ImportJobStatus.PROCESSING,
            ImportJobStatus.READY,
            ImportJobStatus.INVALID,
            ImportJobStatus.CANCELLED,
        }
    ),
    ImportJobStatus.PROCESSING: frozenset(
        {
            ImportJobStatus.READY,
            ImportJobStatus.INVALID,
            ImportJobStatus.APPLIED,
            ImportJobStatus.FAILED,
            ImportJobStatus.CANCELLED,
            ImportJobStatus.PROCESSING,
        }
    ),
    ImportJobStatus.READY: frozenset(
        {
            ImportJobStatus.PROCESSING,
            ImportJobStatus.APPLIED,
            ImportJobStatus.CANCELLED,
            ImportJobStatus.INVALID,
            ImportJobStatus.FAILED,
            ImportJobStatus.READY,
        }
    ),
    ImportJobStatus.INVALID: frozenset(
        {
            ImportJobStatus.PROCESSING,
            ImportJobStatus.READY,
            ImportJobStatus.INVALID,
            ImportJobStatus.CANCELLED,
        }
    ),
    ImportJobStatus.APPLIED: frozenset(),
    ImportJobStatus.CANCELLED: frozenset(),
    ImportJobStatus.FAILED: frozenset(),
}


def propose_mapping(headers: list[str]) -> dict[str, str]:
    proposed: dict[str, str] = {}
    normalized = {header.strip().lower(): header for header in headers if header.strip()}
    for canonical, aliases in NAME_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                proposed[canonical] = normalized[alias]
                break
    return proposed


def validate_mapping(mapping: dict[str, str]) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    seen_headers: dict[str, str] = {}
    for raw_field, raw_header in mapping.items():
        field = raw_field.strip()
        header = raw_header.strip()
        if field not in CANONICAL_FIELDS:
            raise ValidationError(
                "MISSING_COLUMN",
                "El mapping contiene un campo que no es canónico.",
                field_errors=[
                    field_issue(field, "MISSING_COLUMN", "El campo no forma parte de la plantilla.")
                ],
            )
        if not header:
            continue
        if header in seen_headers and seen_headers[header] != field:
            raise ValidationError(
                "DUPLICATE_COLUMN",
                "El mapping repite una columna de origen.",
                field_errors=[
                    field_issue(
                        field, "DUPLICATE_COLUMN", "La misma columna se asignó a más de un campo."
                    )
                ],
            )
        seen_headers[header] = field
        cleaned[field] = header
    missing = [field for field in REQUIRED_FIELDS if field not in cleaned]
    if missing:
        raise ValidationError(
            "MISSING_COLUMN",
            "Faltan columnas requeridas en el mapping.",
            field_errors=[
                field_issue(field, "MISSING_COLUMN", "Esta columna es obligatoria.")
                for field in missing
            ],
        )
    return cleaned


@dataclass(frozen=True, slots=True)
class ImportIssue:
    row_number: int
    field: str
    code: str
    message: str
    raw_value_redacted: str
    severity: ImportErrorSeverity


@dataclass(frozen=True, slots=True)
class ParsedCellRow:
    row_number: int
    values: dict[str, str]
    formula_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NormalizedImportRow:
    row_number: int
    period_start: date
    fiscal_year: int
    account_code: str
    account_name: str | None
    account_type: str | None
    department_code: str
    department_name: str | None
    cost_center_code: str
    cost_center_name: str | None
    amount: MoneyAmount
    currency: str
    source_reference: str | None
    warnings: tuple[ImportIssue, ...]

    def duplicate_key(self) -> tuple[object, ...]:
        return (
            self.period_start,
            self.account_code,
            self.department_code,
            self.cost_center_code,
            self.amount.as_text(),
            self.currency,
            self.source_reference or "",
        )


@dataclass(frozen=True, slots=True)
class ImportJob:
    id: UUID
    organization_id: UUID
    created_by: UUID
    import_type: ScenarioType
    budget_version_id: UUID | None
    status: ImportJobStatus
    original_filename: str
    object_key: str | None
    sha256: str
    size_bytes: int
    media_type: str
    template_version: str
    mapping_json: dict[str, Any]
    row_count: int
    valid_count: int
    error_count: int
    warning_count: int
    period_min: date | None
    period_max: date | None
    valid_amount_total: str
    idempotency_fingerprint: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    failure_code: str | None
    create_missing_dimensions: bool
    sheet_name: str | None
    trace_id: str | None = None

    def _transition(self, status: ImportJobStatus) -> ImportJob:
        if status not in ALLOWED_TRANSITIONS[self.status] and status is not self.status:
            raise ConflictError(
                "IMPORT_STATE",
                "El trabajo de importación no admite esta transición.",
            )
        return replace(self, status=status)

    def mark_processing(self, *, now: datetime, trace_id: str | None = None) -> ImportJob:
        if self.status is ImportJobStatus.PROCESSING:
            return replace(self, started_at=now, trace_id=trace_id or self.trace_id)
        updated = self._transition(ImportJobStatus.PROCESSING)
        return replace(updated, started_at=now, trace_id=trace_id or self.trace_id)

    def mark_timed_out(self, *, now: datetime) -> ImportJob:
        return self.mark_failed(code="JOB_TIMEOUT", now=now)

    def clear_object_key(self) -> ImportJob:
        return replace(self, object_key=None)

    def mark_uploaded(self, *, object_key: str, media_type: str, now: datetime) -> ImportJob:
        if self.status is ImportJobStatus.UPLOADED:
            return replace(self, object_key=object_key, media_type=media_type)
        updated = self._transition(ImportJobStatus.UPLOADED)
        return replace(updated, object_key=object_key, media_type=media_type, started_at=now)

    def mark_validated(
        self,
        *,
        mapping: dict[str, Any],
        fingerprint: str,
        row_count: int,
        valid_count: int,
        error_count: int,
        warning_count: int,
        period_min: date | None,
        period_max: date | None,
        valid_amount_total: str,
        create_missing_dimensions: bool,
        sheet_name: str | None,
        now: datetime,
    ) -> ImportJob:
        if self.status is ImportJobStatus.CREATED:
            raise ConflictError("IMPORT_STATE", "Primero debes cargar el archivo.")
        if self.status in {ImportJobStatus.APPLIED, ImportJobStatus.CANCELLED}:
            raise ConflictError("IMPORT_STATE", "Este trabajo ya no se puede validar.")
        next_status = ImportJobStatus.READY if error_count == 0 else ImportJobStatus.INVALID
        return replace(
            self._transition(next_status),
            mapping_json=mapping,
            idempotency_fingerprint=fingerprint,
            row_count=row_count,
            valid_count=valid_count,
            error_count=error_count,
            warning_count=warning_count,
            period_min=period_min,
            period_max=period_max,
            valid_amount_total=valid_amount_total,
            create_missing_dimensions=create_missing_dimensions,
            sheet_name=sheet_name,
            started_at=self.started_at or now,
            failure_code=None if error_count == 0 else "IMPORT_VALIDATION_FAILED",
        )

    def mark_applied(self, *, now: datetime) -> ImportJob:
        if self.status is ImportJobStatus.APPLIED:
            return self
        return replace(self._transition(ImportJobStatus.APPLIED), completed_at=now)

    def mark_failed(self, *, code: str, now: datetime) -> ImportJob:
        return replace(
            self._transition(ImportJobStatus.FAILED),
            failure_code=code,
            completed_at=now,
        )

    def cancel(self, *, now: datetime) -> ImportJob:
        if self.status is ImportJobStatus.APPLIED:
            raise ConflictError(
                "IMPORT_ALREADY_APPLIED",
                "Un trabajo aplicado no se puede cancelar.",
            )
        if self.status is ImportJobStatus.CANCELLED:
            return self
        return replace(
            self._transition(ImportJobStatus.CANCELLED),
            completed_at=now,
            idempotency_fingerprint=None,
        )

    def assert_committable(self) -> None:
        if self.status is not ImportJobStatus.READY:
            raise ConflictError(
                "IMPORT_NOT_READY",
                "Solo un trabajo validado sin errores se puede aplicar.",
            )
        if self.error_count > 0:
            raise ConflictError(
                "IMPORT_VALIDATION_FAILED",
                "El archivo contiene errores que deben corregirse.",
            )

    def assert_same_hash(self, sha256: str) -> None:
        if self.sha256.lower() != sha256.lower():
            raise ConflictError(
                "IMPORT_HASH_MISMATCH",
                "El archivo cambió después de la validación.",
            )

    def fingerprint_for(self, mapping: dict[str, Any]) -> str:
        return import_idempotency_fingerprint(
            file_sha256=self.sha256,
            mapping=mapping,
            organization_id=self.organization_id,
            scenario_type=self.import_type,
            budget_version_id=self.budget_version_id,
            replacement_scope="append",
        )
