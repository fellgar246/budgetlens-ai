from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from budgetlens.domain.budget_version import BudgetVersion
from budgetlens.domain.dimensions import Account, CostCenter, Department
from budgetlens.domain.enums import Capability, Permission, Role
from budgetlens.domain.organization import Membership, Organization, User
from budgetlens.domain.permissions import capabilities_for as domain_capabilities
from budgetlens.domain.permissions import granted_permissions, persona_for


class PageInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    next_cursor: str | None
    has_more: bool


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    name: str
    slug: str
    functional_currency: str
    fiscal_year_start_month: int
    status: str
    role: str | None = None
    version: int
    conversation_retention_days: int
    created_at: datetime
    updated_at: datetime


class OrganizationListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[OrganizationResponse]
    page: PageInfo


class CreateOrganizationRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "name": "Demo México",
                "slug": "demo-mexico",
                "functional_currency": "MXN",
                "fiscal_year_start_month": 1,
            }
        },
    )
    name: str
    slug: str
    functional_currency: str
    fiscal_year_start_month: int = Field(ge=1, le=12)


class PatchOrganizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    name: str | None = None
    fiscal_year_start_month: int | None = Field(default=None, ge=1, le=12)
    status: Literal["active", "archived"] | None = None
    conversation_retention_days: int | None = Field(default=None, ge=7, le=365)


class Capabilities(BaseModel):
    model_config = ConfigDict(extra="forbid")
    can_view_dashboard: bool
    can_import: bool
    can_publish_budget: bool
    can_create_scenario: bool
    can_use_copilot: bool
    can_manage_members: bool
    can_view_technical_metrics: bool
    can_deploy_rollback: bool
    can_export: bool
    can_manage_versions: bool
    can_manage_dimensions: bool
    can_manage_organization: bool


class MeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    email: str
    display_name: str
    status: str
    auth_mode: str
    role: str | None = None
    persona: str | None = None
    capabilities: Capabilities


class MembershipResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    organization_id: UUID
    user_id: UUID
    role: str
    status: str
    created_at: datetime
    updated_at: datetime


class MembershipListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[MembershipResponse]
    page: PageInfo


class CreateMembershipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    role: Literal["viewer", "analyst", "admin"]


class PatchMembershipRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["viewer", "analyst", "admin"] | None = None
    status: Literal["active", "disabled"] | None = None


class AccountResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    organization_id: UUID
    code: str
    name: str
    account_type: str
    parent_id: UUID | None
    status: str
    created_at: datetime
    updated_at: datetime


class AccountListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[AccountResponse]
    page: PageInfo


class CreateAccountRequest(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "code": "6100",
                "name": "Servicios externos",
                "account_type": "expense",
                "parent_id": None,
            }
        },
    )
    code: str
    name: str
    account_type: Literal["revenue", "expense", "asset", "liability", "equity", "other"]
    parent_id: UUID | None = None


class PatchAccountRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    account_type: Literal["revenue", "expense", "asset", "liability", "equity", "other"] | None = (
        None
    )
    parent_id: UUID | None = None
    clear_parent: bool = False
    status: Literal["active", "inactive"] | None = None


class DepartmentResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    organization_id: UUID
    code: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


class DepartmentListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[DepartmentResponse]
    page: PageInfo


class CreateDepartmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    name: str


class PatchDepartmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    status: Literal["active", "inactive"] | None = None


class CostCenterResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    organization_id: UUID
    code: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


class CostCenterListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[CostCenterResponse]
    page: PageInfo


class CreateCostCenterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str
    name: str


class PatchCostCenterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = None
    status: Literal["active", "inactive"] | None = None


class BudgetVersionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    organization_id: UUID
    name: str
    fiscal_year: int
    status: str
    is_active: bool
    published_at: datetime | None
    published_by: UUID | None
    created_at: datetime
    version: int


class BudgetVersionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[BudgetVersionResponse]
    page: PageInfo


class CreateBudgetVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    fiscal_year: int


class PatchBudgetVersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: int
    name: str


class DevMembership(BaseModel):
    model_config = ConfigDict(extra="forbid")
    organization_id: UUID
    organization_name: str
    role: str


class DevIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: UUID
    email: str
    display_name: str
    platform_role: str | None = None
    memberships: list[DevMembership]


class DevIdentityListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    users: list[DevIdentity]


def organization_response(
    organization: Organization, role: str | None = None
) -> OrganizationResponse:
    return OrganizationResponse(
        id=organization.id,
        name=organization.name,
        slug=organization.slug,
        functional_currency=organization.functional_currency.code,
        fiscal_year_start_month=organization.fiscal_year_start_month,
        status=organization.status.value,
        role=role,
        version=organization.version,
        conversation_retention_days=organization.conversation_retention_days,
        created_at=organization.created_at,
        updated_at=organization.updated_at,
    )


def membership_response(membership: Membership) -> MembershipResponse:
    return MembershipResponse(
        id=membership.id,
        organization_id=membership.organization_id,
        user_id=membership.user_id,
        role=membership.role.value,
        status=membership.status.value,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


def account_response(account: Account) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        organization_id=account.organization_id,
        code=account.code,
        name=account.name,
        account_type=account.account_type.value,
        parent_id=account.parent_id,
        status=account.status.value,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def department_response(department: Department) -> DepartmentResponse:
    return DepartmentResponse(
        id=department.id,
        organization_id=department.organization_id,
        code=department.code,
        name=department.name,
        status=department.status.value,
        created_at=department.created_at,
        updated_at=department.updated_at,
    )


def cost_center_response(item: CostCenter) -> CostCenterResponse:
    return CostCenterResponse(
        id=item.id,
        organization_id=item.organization_id,
        code=item.code,
        name=item.name,
        status=item.status.value,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def budget_version_response(version: BudgetVersion) -> BudgetVersionResponse:
    return BudgetVersionResponse(
        id=version.id,
        organization_id=version.organization_id,
        name=version.name,
        fiscal_year=version.fiscal_year,
        status=version.status.value,
        is_active=version.is_active,
        published_at=version.published_at,
        published_by=version.published_by,
        created_at=version.created_at,
        version=version.version,
    )


def session_capabilities(user: User, role: Role | None) -> Capabilities:
    granted = granted_permissions(role=role, platform_role=user.platform_role)
    product = domain_capabilities(role=role, platform_role=user.platform_role)
    return Capabilities(
        can_view_dashboard=Capability.VIEW_DASHBOARD in product,
        can_import=Capability.IMPORT_ACTUALS in product,
        can_publish_budget=Capability.PUBLISH_BUDGET in product,
        can_create_scenario=Capability.CREATE_SCENARIO in product,
        can_use_copilot=Capability.USE_COPILOT in product,
        can_manage_members=Capability.MANAGE_MEMBERS in product,
        can_view_technical_metrics=Capability.VIEW_TECHNICAL_METRICS in product,
        can_deploy_rollback=Capability.DEPLOY_ROLLBACK in product,
        can_export=Permission.EXPORT in granted,
        can_manage_versions=Permission.MANAGE_VERSIONS in granted,
        can_manage_dimensions=Permission.MANAGE_DIMENSIONS in granted,
        can_manage_organization=Permission.MANAGE_ORGANIZATION in granted,
    )


def me_response(user: User, *, auth_mode: str, role: Role | None) -> MeResponse:
    persona = persona_for(role=role, platform_role=user.platform_role)
    return MeResponse(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        status=user.status.value,
        auth_mode=auth_mode,
        role=role.value if role is not None else None,
        persona=persona.value if persona is not None else None,
        capabilities=session_capabilities(user, role),
    )
