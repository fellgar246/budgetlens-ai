from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date, datetime
from uuid import UUID

from budgetlens.domain.enums import MembershipStatus, OrganizationStatus, Role, UserStatus
from budgetlens.domain.errors import ConflictError, ValidationError
from budgetlens.domain.fiscal import FiscalPeriod, validate_fiscal_year_start_month
from budgetlens.domain.money import Currency

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def normalize_name(value: str, *, field: str, max_length: int) -> str:
    cleaned = " ".join(value.strip().split())
    if not cleaned or len(cleaned) > max_length:
        raise ValidationError(
            "INVALID_NAME",
            "El nombre no es válido.",
            field_errors=[
                {
                    "field": field,
                    "code": "INVALID_NAME",
                    "message": f"El nombre debe tener entre 1 y {max_length} caracteres.",
                }
            ],
        )
    return cleaned


def normalize_slug(value: str) -> str:
    cleaned = value.strip().lower()
    if not _SLUG_RE.match(cleaned) or len(cleaned) > 80:
        raise ValidationError(
            "INVALID_SLUG",
            "El identificador corto solo admite minúsculas, números y guiones.",
            field_errors=[
                {
                    "field": "slug",
                    "code": "INVALID_SLUG",
                    "message": "El identificador corto solo admite minúsculas, números y guiones.",
                }
            ],
        )
    return cleaned


def normalize_email(value: str) -> str:
    cleaned = value.strip()
    if "@" not in cleaned or len(cleaned) > 255:
        raise ValidationError(
            "INVALID_EMAIL",
            "El correo no es válido.",
            field_errors=[
                {"field": "email", "code": "INVALID_EMAIL", "message": "El correo no es válido."}
            ],
        )
    return cleaned


@dataclass(frozen=True, slots=True)
class Organization:
    id: UUID
    name: str
    slug: str
    functional_currency: Currency
    fiscal_year_start_month: int
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime
    version: int

    def period_for(self, value: date) -> FiscalPeriod:
        return FiscalPeriod.from_date(value, self.fiscal_year_start_month)

    def with_updates(
        self,
        *,
        expected_version: int,
        now: datetime,
        name: str | None = None,
        fiscal_year_start_month: int | None = None,
        status: OrganizationStatus | None = None,
    ) -> Organization:
        if expected_version != self.version:
            from budgetlens.domain.errors import ConcurrencyError

            raise ConcurrencyError()
        next_name = (
            normalize_name(name, field="name", max_length=160) if name is not None else self.name
        )
        next_month = (
            validate_fiscal_year_start_month(fiscal_year_start_month)
            if fiscal_year_start_month is not None
            else self.fiscal_year_start_month
        )
        next_status = status if status is not None else self.status
        return replace(
            self,
            name=next_name,
            fiscal_year_start_month=next_month,
            status=next_status,
            updated_at=now,
            version=self.version + 1,
        )


@dataclass(frozen=True, slots=True)
class User:
    id: UUID
    email: str
    display_name: str
    status: UserStatus
    external_subject: str | None
    created_at: datetime
    updated_at: datetime

    def assert_active(self) -> None:
        if self.status is UserStatus.DISABLED:
            from budgetlens.domain.errors import UnauthenticatedError

            raise UnauthenticatedError("La cuenta está deshabilitada.")


@dataclass(frozen=True, slots=True)
class Membership:
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: Role
    status: MembershipStatus
    created_at: datetime
    updated_at: datetime

    def is_active(self) -> bool:
        return self.status is MembershipStatus.ACTIVE

    def with_updates(
        self,
        *,
        now: datetime,
        role: Role | None = None,
        status: MembershipStatus | None = None,
    ) -> Membership:
        return replace(
            self,
            role=role if role is not None else self.role,
            status=status if status is not None else self.status,
            updated_at=now,
        )


def require_active_admin_remains(
    memberships: list[Membership],
    *,
    changing: Membership,
    next_role: Role,
    next_status: MembershipStatus,
) -> None:
    active_admins = [
        item
        for item in memberships
        if item.is_active() and item.role is Role.ADMIN and item.id != changing.id
    ]
    still_admin = next_status is MembershipStatus.ACTIVE and next_role is Role.ADMIN
    if not active_admins and not still_admin:
        raise ConflictError(
            "LAST_ADMIN",
            "La organización debe conservar al menos un administrador activo.",
        )
