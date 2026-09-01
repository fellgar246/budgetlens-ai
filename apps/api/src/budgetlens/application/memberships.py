from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.repositories import (
    SqlAuditRepository,
    SqlMembershipRepository,
    SqlUserRepository,
)
from budgetlens.application.audit import record_audit
from budgetlens.application.context import TenantContext
from budgetlens.application.pagination import Page, clamp_limit
from budgetlens.domain.audit import MEMBERSHIP_CREATED, MEMBERSHIP_DISABLED, MEMBERSHIP_ROLE_CHANGED
from budgetlens.domain.enums import MembershipStatus, Permission, Role
from budgetlens.domain.errors import ConflictError, NotFoundError
from budgetlens.domain.identities import Clock, IdFactory
from budgetlens.domain.organization import Membership, require_active_admin_remains
from budgetlens.domain.permissions import require_permission


class MembershipService:
    def __init__(self, session: Session, clock: Clock, ids: IdFactory) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids
        self._users = SqlUserRepository(session)
        self._audits = SqlAuditRepository(session)

    def _repo(self, organization_id: UUID) -> SqlMembershipRepository:
        return SqlMembershipRepository(self._session, organization_id)

    def list(
        self, context: TenantContext, *, cursor: str | None, limit: int | None
    ) -> Page[Membership]:
        return self._repo(context.organization_id).list_page(
            cursor=cursor, limit=clamp_limit(limit)
        )

    def create(self, context: TenantContext, *, user_id: UUID, role: Role) -> Membership:
        require_permission(context.role, Permission.MANAGE_MEMBERS)
        if self._users.get(user_id) is None:
            raise NotFoundError("No se encontró el usuario.")
        repo = self._repo(context.organization_id)
        if repo.get_for_user(user_id) is not None:
            raise ConflictError("MEMBERSHIP_EXISTS", "El usuario ya pertenece a esta organización.")
        now = self._clock.now()
        membership = Membership(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            user_id=user_id,
            role=role,
            status=MembershipStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )
        try:
            repo.add(membership)
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "MEMBERSHIP_EXISTS",
                "El usuario ya pertenece a esta organización.",
            ) from exc
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action=MEMBERSHIP_CREATED,
            resource_type="membership",
            resource_id=membership.id,
            trace_id=context.trace_id,
            metadata={"role": role.value},
        )
        return membership

    def update(
        self,
        context: TenantContext,
        *,
        membership_id: UUID,
        role: Role | None,
        status: MembershipStatus | None,
    ) -> Membership:
        require_permission(context.role, Permission.MANAGE_MEMBERS)
        repo = self._repo(context.organization_id)
        current = repo.get(membership_id)
        if current is None:
            raise NotFoundError()
        next_role = role if role is not None else current.role
        next_status = status if status is not None else current.status
        require_active_admin_remains(
            repo.list_active_admins(),
            changing=current,
            next_role=next_role,
            next_status=next_status,
        )
        updated = current.with_updates(now=self._clock.now(), role=role, status=status)
        repo.save(updated)
        if (
            updated.status is MembershipStatus.DISABLED
            and current.status is not MembershipStatus.DISABLED
        ):
            action = MEMBERSHIP_DISABLED
        else:
            action = MEMBERSHIP_ROLE_CHANGED
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action=action,
            resource_type="membership",
            resource_id=updated.id,
            trace_id=context.trace_id,
            metadata={
                "before": {"role": current.role.value, "status": current.status.value},
                "after": {"role": updated.role.value, "status": updated.status.value},
            },
        )
        return updated
