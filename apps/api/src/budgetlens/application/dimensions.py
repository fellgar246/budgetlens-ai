from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.repositories import (
    SqlAccountRepository,
    SqlCostCenterRepository,
    SqlDepartmentRepository,
)
from budgetlens.application.context import TenantContext
from budgetlens.application.pagination import Page, clamp_limit
from budgetlens.domain.dimensions import (
    Account,
    CostCenter,
    Department,
    assert_account_hierarchy,
    normalize_code,
)
from budgetlens.domain.enums import AccountType, DimensionStatus, Permission
from budgetlens.domain.errors import ConflictError, NotFoundError
from budgetlens.domain.identities import Clock, IdFactory
from budgetlens.domain.organization import normalize_name
from budgetlens.domain.permissions import require_dimension_restructure, require_permission


class DimensionService:
    def __init__(self, session: Session, clock: Clock, ids: IdFactory) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids

    def list_accounts(
        self,
        context: TenantContext,
        *,
        cursor: str | None,
        limit: int | None,
        status: str | None,
        search: str | None,
    ) -> Page[Account]:
        return SqlAccountRepository(self._session, context.organization_id).list_page(
            cursor=cursor,
            limit=clamp_limit(limit),
            status=status,
            search=search,
        )

    def get_account(self, context: TenantContext, account_id: UUID) -> Account:
        account = SqlAccountRepository(self._session, context.organization_id).get(account_id)
        if account is None:
            raise NotFoundError()
        return account

    def create_account(
        self,
        context: TenantContext,
        *,
        code: str,
        name: str,
        account_type: AccountType,
        parent_id: UUID | None,
    ) -> Account:
        require_permission(context.role, Permission.MANAGE_DIMENSIONS)
        repo = SqlAccountRepository(self._session, context.organization_id)
        normalized = normalize_code(code)
        if repo.get_by_code(normalized) is not None:
            raise ConflictError(
                "CODE_TAKEN",
                "El código de cuenta ya existe en esta organización.",
            )
        if parent_id is not None and repo.get(parent_id) is None:
            raise NotFoundError("No se encontró la cuenta superior.")
        account_id = self._ids.new_id()
        assert_account_hierarchy(
            account_id=account_id,
            parent_id=parent_id,
            ancestors=repo.ancestor_ids(parent_id),
        )
        now = self._clock.now()
        account = Account(
            id=account_id,
            organization_id=context.organization_id,
            code=normalized,
            name=normalize_name(name, field="name", max_length=160),
            account_type=account_type,
            parent_id=parent_id,
            status=DimensionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        try:
            repo.add(account)
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "CODE_TAKEN",
                "El código de cuenta ya existe en esta organización.",
            ) from exc
        return account

    def update_account(
        self,
        context: TenantContext,
        *,
        account_id: UUID,
        name: str | None,
        account_type: AccountType | None,
        parent_id: UUID | None,
        clear_parent: bool,
        status: DimensionStatus | None,
    ) -> Account:
        require_permission(context.role, Permission.MANAGE_DIMENSIONS)
        repo = SqlAccountRepository(self._session, context.organization_id)
        current = repo.get(account_id)
        if current is None:
            raise NotFoundError()
        structural = (
            account_type is not None or parent_id is not None or clear_parent or status is not None
        )
        if structural:
            require_dimension_restructure(context.role)
        next_parent = None if clear_parent else parent_id or current.parent_id
        if next_parent is not None and repo.get(next_parent) is None:
            raise NotFoundError("No se encontró la cuenta superior.")
        assert_account_hierarchy(
            account_id=current.id,
            parent_id=next_parent,
            ancestors=repo.ancestor_ids(next_parent),
        )
        updated = current.with_updates(
            now=self._clock.now(),
            name=name,
            account_type=account_type,
            parent_id=next_parent,
            clear_parent=clear_parent,
            status=status,
        )
        repo.save(updated)
        return updated

    def list_departments(
        self,
        context: TenantContext,
        *,
        cursor: str | None,
        limit: int | None,
        status: str | None,
        search: str | None,
    ) -> Page[Department]:
        return SqlDepartmentRepository(self._session, context.organization_id).list_page(
            cursor=cursor,
            limit=clamp_limit(limit),
            status=status,
            search=search,
        )

    def get_department(self, context: TenantContext, department_id: UUID) -> Department:
        repo = SqlDepartmentRepository(self._session, context.organization_id)
        department = repo.get(department_id)
        if department is None:
            raise NotFoundError()
        return department

    def create_department(self, context: TenantContext, *, code: str, name: str) -> Department:
        require_permission(context.role, Permission.MANAGE_DIMENSIONS)
        repo = SqlDepartmentRepository(self._session, context.organization_id)
        normalized = normalize_code(code)
        if repo.get_by_code(normalized) is not None:
            raise ConflictError(
                "CODE_TAKEN",
                "El código de departamento ya existe en esta organización.",
            )
        now = self._clock.now()
        department = Department(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            code=normalized,
            name=normalize_name(name, field="name", max_length=160),
            status=DimensionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        try:
            repo.add(department)
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "CODE_TAKEN",
                "El código de departamento ya existe en esta organización.",
            ) from exc
        return department

    def update_department(
        self,
        context: TenantContext,
        *,
        department_id: UUID,
        name: str | None,
        status: DimensionStatus | None,
    ) -> Department:
        require_permission(context.role, Permission.MANAGE_DIMENSIONS)
        repo = SqlDepartmentRepository(self._session, context.organization_id)
        current = repo.get(department_id)
        if current is None:
            raise NotFoundError()
        if status is not None:
            require_dimension_restructure(context.role)
        updated = current.with_updates(now=self._clock.now(), name=name, status=status)
        repo.save(updated)
        return updated

    def list_cost_centers(
        self,
        context: TenantContext,
        *,
        cursor: str | None,
        limit: int | None,
        status: str | None,
        search: str | None,
    ) -> Page[CostCenter]:
        return SqlCostCenterRepository(self._session, context.organization_id).list_page(
            cursor=cursor,
            limit=clamp_limit(limit),
            status=status,
            search=search,
        )

    def get_cost_center(self, context: TenantContext, cost_center_id: UUID) -> CostCenter:
        item = SqlCostCenterRepository(self._session, context.organization_id).get(cost_center_id)
        if item is None:
            raise NotFoundError()
        return item

    def create_cost_center(self, context: TenantContext, *, code: str, name: str) -> CostCenter:
        require_permission(context.role, Permission.MANAGE_DIMENSIONS)
        repo = SqlCostCenterRepository(self._session, context.organization_id)
        normalized = normalize_code(code)
        if repo.get_by_code(normalized) is not None:
            raise ConflictError(
                "CODE_TAKEN",
                "El código de centro de costo ya existe en esta organización.",
            )
        now = self._clock.now()
        item = CostCenter(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            code=normalized,
            name=normalize_name(name, field="name", max_length=160),
            status=DimensionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        try:
            repo.add(item)
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "CODE_TAKEN",
                "El código de centro de costo ya existe en esta organización.",
            ) from exc
        return item

    def update_cost_center(
        self,
        context: TenantContext,
        *,
        cost_center_id: UUID,
        name: str | None,
        status: DimensionStatus | None,
        code: str | None,
    ) -> CostCenter:
        require_permission(context.role, Permission.MANAGE_DIMENSIONS)
        repo = SqlCostCenterRepository(self._session, context.organization_id)
        current = repo.get(cost_center_id)
        if current is None:
            raise NotFoundError()
        if status is not None or code is not None:
            require_dimension_restructure(context.role)
        updated = current.with_updates(now=self._clock.now(), name=name, status=status, code=code)
        repo.save(updated)
        return updated
