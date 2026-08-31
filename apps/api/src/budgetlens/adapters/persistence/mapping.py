from __future__ import annotations

from budgetlens.adapters.persistence.models import (
    AccountRow,
    AuditEventRow,
    BudgetVersionRow,
    CostCenterRow,
    DepartmentRow,
    MembershipRow,
    OrganizationRow,
    UserRow,
)
from budgetlens.domain.audit import AuditEvent
from budgetlens.domain.budget_version import BudgetVersion
from budgetlens.domain.dimensions import Account, CostCenter, Department
from budgetlens.domain.enums import (
    AccountType,
    BudgetVersionStatus,
    DimensionStatus,
    MembershipStatus,
    OrganizationStatus,
    Role,
    UserStatus,
)
from budgetlens.domain.money import Currency
from budgetlens.domain.organization import Membership, Organization, User


def user_from_row(row: UserRow) -> User:
    return User(
        id=row.id,
        email=str(row.email),
        display_name=row.display_name,
        status=UserStatus(row.status),
        external_subject=row.external_subject,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def apply_user(row: UserRow, entity: User) -> None:
    row.id = entity.id
    row.email = entity.email
    row.display_name = entity.display_name
    row.status = entity.status.value
    row.external_subject = entity.external_subject
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at


def organization_from_row(row: OrganizationRow) -> Organization:
    return Organization(
        id=row.id,
        name=row.name,
        slug=row.slug,
        functional_currency=Currency(row.functional_currency),
        fiscal_year_start_month=row.fiscal_year_start_month,
        status=OrganizationStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        version=row.version,
    )


def apply_organization(row: OrganizationRow, entity: Organization) -> None:
    row.id = entity.id
    row.name = entity.name
    row.slug = entity.slug
    row.functional_currency = entity.functional_currency.code
    row.fiscal_year_start_month = entity.fiscal_year_start_month
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at
    row.version = entity.version


def membership_from_row(row: MembershipRow) -> Membership:
    return Membership(
        id=row.id,
        organization_id=row.organization_id,
        user_id=row.user_id,
        role=Role(row.role),
        status=MembershipStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def apply_membership(row: MembershipRow, entity: Membership) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.user_id = entity.user_id
    row.role = entity.role.value
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at


def account_from_row(row: AccountRow) -> Account:
    return Account(
        id=row.id,
        organization_id=row.organization_id,
        code=row.code,
        name=row.name,
        account_type=AccountType(row.account_type),
        parent_id=row.parent_id,
        status=DimensionStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def apply_account(row: AccountRow, entity: Account) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.code = entity.code
    row.name = entity.name
    row.account_type = entity.account_type.value
    row.parent_id = entity.parent_id
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at


def department_from_row(row: DepartmentRow) -> Department:
    return Department(
        id=row.id,
        organization_id=row.organization_id,
        code=row.code,
        name=row.name,
        status=DimensionStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def apply_department(row: DepartmentRow, entity: Department) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.code = entity.code
    row.name = entity.name
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at


def cost_center_from_row(row: CostCenterRow) -> CostCenter:
    return CostCenter(
        id=row.id,
        organization_id=row.organization_id,
        code=row.code,
        name=row.name,
        status=DimensionStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def apply_cost_center(row: CostCenterRow, entity: CostCenter) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.code = entity.code
    row.name = entity.name
    row.status = entity.status.value
    row.created_at = entity.created_at
    row.updated_at = entity.updated_at


def budget_version_from_row(row: BudgetVersionRow) -> BudgetVersion:
    return BudgetVersion(
        id=row.id,
        organization_id=row.organization_id,
        name=row.name,
        fiscal_year=row.fiscal_year,
        status=BudgetVersionStatus(row.status),
        is_active=row.is_active,
        published_at=row.published_at,
        published_by=row.published_by,
        created_at=row.created_at,
        version=row.version,
    )


def apply_budget_version(row: BudgetVersionRow, entity: BudgetVersion) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.name = entity.name
    row.fiscal_year = entity.fiscal_year
    row.status = entity.status.value
    row.is_active = entity.is_active
    row.published_at = entity.published_at
    row.published_by = entity.published_by
    row.created_at = entity.created_at
    row.version = entity.version


def audit_from_row(row: AuditEventRow) -> AuditEvent:
    return AuditEvent(
        id=row.id,
        organization_id=row.organization_id,
        actor_id=row.actor_id,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        outcome=row.outcome,
        metadata=dict(row.metadata_json),
        trace_id=row.trace_id,
        created_at=row.created_at,
        schema_version=row.schema_version,
    )


def apply_audit(row: AuditEventRow, entity: AuditEvent) -> None:
    row.id = entity.id
    row.organization_id = entity.organization_id
    row.actor_id = entity.actor_id
    row.action = entity.action
    row.resource_type = entity.resource_type
    row.resource_id = entity.resource_id
    row.outcome = entity.outcome
    row.metadata_json = entity.metadata
    row.trace_id = entity.trace_id
    row.created_at = entity.created_at
    row.schema_version = entity.schema_version
    row.ip_hash = None
