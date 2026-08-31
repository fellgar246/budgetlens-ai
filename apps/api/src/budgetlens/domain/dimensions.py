from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from budgetlens.domain.enums import (
    ACCOUNT_HIERARCHY_MAX_DEPTH,
    UNASSIGNED_CODE,
    AccountType,
    DimensionStatus,
)
from budgetlens.domain.errors import ConflictError, ValidationError
from budgetlens.domain.organization import normalize_name


def normalize_code(value: str, *, field: str = "code") -> str:
    cleaned = value.strip()
    if not cleaned or len(cleaned) > 64:
        raise ValidationError(
            "INVALID_CODE",
            "El código no es válido.",
            field_errors=[
                {
                    "field": field,
                    "code": "INVALID_CODE",
                    "message": "El código debe tener entre 1 y 64 caracteres.",
                }
            ],
        )
    return cleaned


def resolve_cost_center_code(code: str | None) -> str:
    if code is None or not code.strip():
        return UNASSIGNED_CODE
    return normalize_code(code, field="cost_center_code")


@dataclass(frozen=True, slots=True)
class Account:
    id: UUID
    organization_id: UUID
    code: str
    name: str
    account_type: AccountType
    parent_id: UUID | None
    status: DimensionStatus
    created_at: datetime
    updated_at: datetime

    def with_updates(
        self,
        *,
        now: datetime,
        name: str | None = None,
        account_type: AccountType | None = None,
        parent_id: UUID | None = None,
        clear_parent: bool = False,
        status: DimensionStatus | None = None,
    ) -> Account:
        if clear_parent:
            next_parent = None
        elif parent_id is not None:
            next_parent = parent_id
        else:
            next_parent = self.parent_id
        return replace(
            self,
            name=(
                normalize_name(name, field="name", max_length=160)
                if name is not None
                else self.name
            ),
            account_type=account_type if account_type is not None else self.account_type,
            parent_id=next_parent,
            status=status if status is not None else self.status,
            updated_at=now,
        )


@dataclass(frozen=True, slots=True)
class Department:
    id: UUID
    organization_id: UUID
    code: str
    name: str
    status: DimensionStatus
    created_at: datetime
    updated_at: datetime

    def with_updates(
        self,
        *,
        now: datetime,
        name: str | None = None,
        status: DimensionStatus | None = None,
    ) -> Department:
        return replace(
            self,
            name=(
                normalize_name(name, field="name", max_length=160)
                if name is not None
                else self.name
            ),
            status=status if status is not None else self.status,
            updated_at=now,
        )


@dataclass(frozen=True, slots=True)
class CostCenter:
    id: UUID
    organization_id: UUID
    code: str
    name: str
    status: DimensionStatus
    created_at: datetime
    updated_at: datetime

    @property
    def is_unassigned(self) -> bool:
        return self.code == UNASSIGNED_CODE

    def with_updates(
        self,
        *,
        now: datetime,
        name: str | None = None,
        status: DimensionStatus | None = None,
        code: str | None = None,
    ) -> CostCenter:
        if self.is_unassigned:
            if code is not None and normalize_code(code) != UNASSIGNED_CODE:
                raise ConflictError(
                    "UNASSIGNED_PROTECTED",
                    "La dimensión Sin asignar no puede cambiar de código.",
                )
            if status is DimensionStatus.INACTIVE:
                raise ConflictError(
                    "UNASSIGNED_PROTECTED",
                    "La dimensión Sin asignar debe permanecer activa.",
                )
        return replace(
            self,
            name=(
                normalize_name(name, field="name", max_length=160)
                if name is not None
                else self.name
            ),
            status=status if status is not None else self.status,
            updated_at=now,
        )


def assert_account_hierarchy(
    *,
    account_id: UUID,
    parent_id: UUID | None,
    ancestors: list[UUID],
) -> None:
    if parent_id is None:
        return
    if parent_id == account_id or account_id in ancestors:
        raise ValidationError(
            "ACCOUNT_CYCLE",
            "La cuenta superior formaría un ciclo.",
            field_errors=[
                {
                    "field": "parent_id",
                    "code": "ACCOUNT_CYCLE",
                    "message": "La cuenta superior formaría un ciclo.",
                }
            ],
        )
    depth = 1 + len(ancestors)
    if depth > ACCOUNT_HIERARCHY_MAX_DEPTH:
        raise ValidationError(
            "ACCOUNT_DEPTH",
            "La jerarquía de cuentas no puede superar cinco niveles.",
            field_errors=[
                {
                    "field": "parent_id",
                    "code": "ACCOUNT_DEPTH",
                    "message": "La jerarquía de cuentas no puede superar cinco niveles.",
                }
            ],
        )


def build_unassigned_cost_center(
    *,
    organization_id: UUID,
    cost_center_id: UUID,
    now: datetime,
) -> CostCenter:
    return CostCenter(
        id=cost_center_id,
        organization_id=organization_id,
        code=UNASSIGNED_CODE,
        name="Sin asignar",
        status=DimensionStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
