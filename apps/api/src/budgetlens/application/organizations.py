from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.repositories import (
    SqlAuditRepository,
    SqlCostCenterRepository,
    SqlMembershipRepository,
    SqlOrganizationRepository,
    SqlUserRepository,
)
from budgetlens.adapters.tenancy import apply_tenant_gucs
from budgetlens.application.audit import record_audit
from budgetlens.application.context import TenantContext
from budgetlens.application.pagination import Page, clamp_limit
from budgetlens.domain.audit import (
    MEMBERSHIP_CREATED,
    ORGANIZATION_ARCHIVED,
    ORGANIZATION_CREATED,
    ORGANIZATION_UPDATED,
)
from budgetlens.domain.dimensions import build_unassigned_cost_center
from budgetlens.domain.enums import (
    MembershipStatus,
    OrganizationStatus,
    Permission,
    PlatformRole,
    Role,
)
from budgetlens.domain.errors import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    UnauthenticatedError,
)
from budgetlens.domain.fiscal import validate_fiscal_year_start_month
from budgetlens.domain.identities import Clock, IdFactory
from budgetlens.domain.money import Currency
from budgetlens.domain.organization import (
    CONVERSATION_RETENTION_DEFAULT_DAYS,
    Membership,
    Organization,
    User,
    normalize_name,
    normalize_slug,
)
from budgetlens.domain.permissions import require_permission


class OrganizationService:
    def __init__(self, session: Session, clock: Clock, ids: IdFactory) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids
        self._orgs = SqlOrganizationRepository(session)
        self._users = SqlUserRepository(session)
        self._audits = SqlAuditRepository(session)

    def list_for_user(
        self, user: User, *, cursor: str | None, limit: int | None
    ) -> Page[tuple[Organization, Membership]]:
        return self._orgs.list_for_user(user.id, cursor=cursor, limit=clamp_limit(limit))

    def get(self, context: TenantContext, organization_id: object) -> Organization:
        if organization_id != context.organization_id:
            raise NotFoundError()
        organization = self._orgs.get(context.organization_id)
        if organization is None:
            raise NotFoundError()
        return organization

    def create(
        self,
        user: User,
        *,
        name: str,
        slug: str,
        functional_currency: str,
        fiscal_year_start_month: int,
        trace_id: str,
    ) -> Organization:
        if user.platform_role is PlatformRole.OPERATOR:
            raise PermissionDeniedError()
        now = self._clock.now()
        organization = Organization(
            id=self._ids.new_id(),
            name=normalize_name(name, field="name", max_length=160),
            slug=normalize_slug(slug),
            functional_currency=Currency(functional_currency),
            fiscal_year_start_month=validate_fiscal_year_start_month(fiscal_year_start_month),
            status=OrganizationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            version=1,
            conversation_retention_days=CONVERSATION_RETENTION_DEFAULT_DAYS,
        )
        if self._orgs.get_by_slug(organization.slug) is not None:
            raise ConflictError("SLUG_TAKEN", "Ya existe una organización con ese identificador.")
        apply_tenant_gucs(
            self._session,
            user_id=user.id,
            organization_id=organization.id,
        )
        memberships = SqlMembershipRepository(self._session, organization.id)
        cost_centers = SqlCostCenterRepository(self._session, organization.id)
        membership = Membership(
            id=self._ids.new_id(),
            organization_id=organization.id,
            user_id=user.id,
            role=Role.ADMIN,
            status=MembershipStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        try:
            self._orgs.add(organization)
            memberships.add(membership)
            cost_centers.add(
                build_unassigned_cost_center(
                    organization_id=organization.id,
                    cost_center_id=self._ids.new_id(),
                    now=now,
                )
            )
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "SLUG_TAKEN",
                "Ya existe una organización con ese identificador.",
            ) from exc
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=organization.id,
            actor_id=user.id,
            action=ORGANIZATION_CREATED,
            resource_type="organization",
            resource_id=organization.id,
            trace_id=trace_id,
            metadata={"slug": organization.slug},
        )
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=organization.id,
            actor_id=user.id,
            action=MEMBERSHIP_CREATED,
            resource_type="membership",
            resource_id=membership.id,
            trace_id=trace_id,
            metadata={"role": membership.role.value, "status": membership.status.value},
        )
        return organization

    def update(
        self,
        context: TenantContext,
        *,
        organization_id: object,
        version: int,
        name: str | None,
        fiscal_year_start_month: int | None,
        status: OrganizationStatus | None,
        conversation_retention_days: int | None = None,
    ) -> Organization:
        require_permission(context.role, Permission.MANAGE_ORGANIZATION)
        if organization_id != context.organization_id:
            raise NotFoundError()
        current = self._orgs.get(context.organization_id)
        if current is None:
            raise NotFoundError()
        updated = current.with_updates(
            expected_version=version,
            now=self._clock.now(),
            name=name,
            fiscal_year_start_month=fiscal_year_start_month,
            status=status,
            conversation_retention_days=conversation_retention_days,
        )
        self._orgs.save(updated)
        action = (
            ORGANIZATION_ARCHIVED
            if updated.status is OrganizationStatus.ARCHIVED
            and current.status is not OrganizationStatus.ARCHIVED
            else ORGANIZATION_UPDATED
        )
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=updated.id,
            actor_id=context.user.id,
            action=action,
            resource_type="organization",
            resource_id=updated.id,
            trace_id=context.trace_id,
            metadata={
                "version": updated.version,
                "before": {"status": current.status.value},
                "after": {"status": updated.status.value},
            },
        )
        return updated


def require_active_user(user: User | None) -> User:
    if user is None:
        raise UnauthenticatedError()
    user.assert_active()
    return user
