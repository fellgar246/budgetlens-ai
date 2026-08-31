from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.models import IdempotencyRecordRow
from budgetlens.adapters.persistence.repositories import (
    SqlAuditRepository,
    SqlBudgetVersionRepository,
    SqlIdempotencyRepository,
)
from budgetlens.application.audit import record_audit
from budgetlens.application.context import TenantContext
from budgetlens.application.pagination import Page, clamp_limit
from budgetlens.domain.budget_version import BudgetVersion
from budgetlens.domain.enums import BudgetVersionStatus, Permission
from budgetlens.domain.errors import ConflictError, NotFoundError, ValidationError
from budgetlens.domain.idempotency import sha256_hex
from budgetlens.domain.identities import Clock, IdFactory
from budgetlens.domain.organization import normalize_name
from budgetlens.domain.permissions import require_permission


class BudgetVersionService:
    def __init__(self, session: Session, clock: Clock, ids: IdFactory) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids
        self._audits = SqlAuditRepository(session)

    def _repo(self, organization_id: UUID) -> SqlBudgetVersionRepository:
        return SqlBudgetVersionRepository(self._session, organization_id)

    def list(
        self,
        context: TenantContext,
        *,
        cursor: str | None,
        limit: int | None,
        fiscal_year: int | None,
        include_archived: bool,
    ) -> Page[BudgetVersion]:
        return self._repo(context.organization_id).list_page(
            cursor=cursor,
            limit=clamp_limit(limit),
            fiscal_year=fiscal_year,
            include_archived=include_archived,
        )

    def get(self, context: TenantContext, version_id: UUID) -> BudgetVersion:
        version = self._repo(context.organization_id).get(version_id)
        if version is None:
            raise NotFoundError()
        return version

    def create(self, context: TenantContext, *, name: str, fiscal_year: int) -> BudgetVersion:
        require_permission(context.role, Permission.MANAGE_VERSIONS)
        repo = self._repo(context.organization_id)
        cleaned = normalize_name(name, field="name", max_length=160)
        if repo.get_by_name(fiscal_year, cleaned) is not None:
            raise ConflictError(
                "VERSION_NAME_TAKEN",
                "Ya existe una versión con ese nombre en el año fiscal.",
            )
        version = BudgetVersion(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            name=cleaned,
            fiscal_year=fiscal_year,
            status=BudgetVersionStatus.DRAFT,
            is_active=False,
            published_at=None,
            published_by=None,
            created_at=self._clock.now(),
            version=1,
        )
        try:
            repo.add(version)
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "VERSION_NAME_TAKEN",
                "Ya existe una versión con ese nombre en el año fiscal.",
            ) from exc
        return version

    def update(
        self,
        context: TenantContext,
        *,
        version_id: UUID,
        expected_version: int,
        name: str,
    ) -> BudgetVersion:
        require_permission(context.role, Permission.MANAGE_VERSIONS)
        repo = self._repo(context.organization_id)
        current = repo.get(version_id)
        if current is None:
            raise NotFoundError()
        updated = current.with_draft_metadata(expected_version=expected_version, name=name)
        try:
            repo.save(updated)
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "VERSION_NAME_TAKEN",
                "Ya existe una versión con ese nombre en el año fiscal.",
            ) from exc
        return updated

    def publish(
        self,
        context: TenantContext,
        *,
        version_id: UUID,
        idempotency_key: str,
    ) -> BudgetVersion:
        require_permission(context.role, Permission.MANAGE_VERSIONS)
        return self._transition(
            context,
            version_id=version_id,
            idempotency_key=idempotency_key,
            operation="budget_version.publish",
            apply=lambda current: current.publish(now=self._clock.now(), actor_id=context.user.id),
        )

    def activate(
        self,
        context: TenantContext,
        *,
        version_id: UUID,
        idempotency_key: str,
    ) -> BudgetVersion:
        require_permission(context.role, Permission.MANAGE_VERSIONS)
        repo = self._repo(context.organization_id)
        current = repo.get(version_id)
        if current is None:
            raise NotFoundError()
        replay = self._replay_or_reserve(
            context,
            operation="budget_version.activate",
            idempotency_key=idempotency_key,
            resource_id=current.id,
        )
        if replay is not None:
            existing = repo.get(replay)
            if existing is None:
                raise NotFoundError()
            return existing
        previous = repo.get_active(current.fiscal_year)
        if previous is not None and previous.id != current.id:
            repo.save(previous.deactivate())
            self._session.flush()
        updated = current.activate()
        try:
            repo.save(updated)
            self._session.flush()
        except IntegrityError as exc:
            raise ConflictError(
                "ACTIVE_VERSION_EXISTS",
                "Solo una versión publicada puede estar activa por año fiscal.",
            ) from exc
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action="budget_version.activate",
            resource_type="budget_version",
            resource_id=updated.id,
            trace_id=context.trace_id,
            metadata={
                "fiscal_year": updated.fiscal_year,
                "previous_id": str(previous.id) if previous else None,
            },
        )
        return updated

    def archive(
        self,
        context: TenantContext,
        *,
        version_id: UUID,
        idempotency_key: str,
    ) -> BudgetVersion:
        require_permission(context.role, Permission.MANAGE_VERSIONS)
        return self._transition(
            context,
            version_id=version_id,
            idempotency_key=idempotency_key,
            operation="budget_version.archive",
            apply=lambda current: current.archive(now=self._clock.now()),
        )

    def _transition(
        self,
        context: TenantContext,
        *,
        version_id: UUID,
        idempotency_key: str,
        operation: str,
        apply: Callable[[BudgetVersion], BudgetVersion],
    ) -> BudgetVersion:
        repo = self._repo(context.organization_id)
        current = repo.get(version_id)
        if current is None:
            raise NotFoundError()
        replay = self._replay_or_reserve(
            context,
            operation=operation,
            idempotency_key=idempotency_key,
            resource_id=current.id,
        )
        if replay is not None:
            existing = repo.get(replay)
            if existing is None:
                raise NotFoundError()
            return existing
        updated = apply(current)
        repo.save(updated)
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action=operation,
            resource_type="budget_version",
            resource_id=updated.id,
            trace_id=context.trace_id,
            metadata={"status": updated.status.value},
        )
        return updated

    def _replay_or_reserve(
        self,
        context: TenantContext,
        *,
        operation: str,
        idempotency_key: str,
        resource_id: UUID,
    ) -> UUID | None:
        key = _require_idempotency_key(idempotency_key)
        request_hash = sha256_hex(f"{operation}:{resource_id}".encode())
        store = SqlIdempotencyRepository(self._session, context.organization_id)
        existing = store.get(user_id=context.user.id, operation=operation, key=key)
        if existing is not None:
            if existing.request_hash != request_hash:
                raise ConflictError(
                    "IDEMPOTENCY_CONFLICT",
                    "La clave de idempotencia ya se usó con otra solicitud.",
                )
            return existing.resource_id
        store.add(
            IdempotencyRecordRow(
                id=self._ids.new_id(),
                organization_id=context.organization_id,
                user_id=context.user.id,
                operation=operation,
                key=key,
                request_hash=request_hash,
                resource_id=resource_id,
                created_at=self._clock.now(),
            )
        )
        return None


def _require_idempotency_key(value: str | None) -> str:
    cleaned = (value or "").strip()
    if not cleaned or len(cleaned) > 128:
        raise ValidationError(
            "IDEMPOTENCY_KEY_REQUIRED",
            "Esta acción requiere una clave de idempotencia.",
            field_errors=[
                {
                    "field": "Idempotency-Key",
                    "code": "IDEMPOTENCY_KEY_REQUIRED",
                    "message": "Esta acción requiere una clave de idempotencia.",
                }
            ],
        )
    return cleaned
