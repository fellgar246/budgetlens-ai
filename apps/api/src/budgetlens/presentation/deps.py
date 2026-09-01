from __future__ import annotations

from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from budgetlens.adapters.db import get_session_factory
from budgetlens.adapters.factory import (
    build_ai_provider,
    build_identity_adapter,
    build_import_runner,
    build_object_storage,
    build_workbook_parser,
)
from budgetlens.adapters.persistence.repositories import (
    SqlMembershipRepository,
    SqlOrganizationRepository,
)
from budgetlens.application.ai import ConversationService
from budgetlens.application.analytics import AnalyticsService
from budgetlens.application.budget_versions import BudgetVersionService
from budgetlens.application.context import TenantContext
from budgetlens.application.dimensions import DimensionService
from budgetlens.application.imports import ImportService
from budgetlens.application.memberships import MembershipService
from budgetlens.application.organizations import OrganizationService
from budgetlens.application.scenarios import ScenarioService
from budgetlens.config import Settings, get_settings
from budgetlens.domain.errors import NotFoundError, PermissionDeniedError, UnauthenticatedError
from budgetlens.domain.identities import Clock, IdFactory, SystemClock, Uuid4Factory
from budgetlens.domain.organization import User
from budgetlens.observability import metrics_registry
from budgetlens.ports.identity import IdentityProvider
from budgetlens.ports.imports import ImportExecutor
from budgetlens.ports.parsing import WorkbookParser
from budgetlens.ports.storage import ObjectStorage


def get_db_session() -> Generator[Session, None, None]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        metrics_registry().record_rollback()
        raise
    finally:
        session.close()


def get_clock() -> Clock:
    return SystemClock()


def get_ids() -> IdFactory:
    return Uuid4Factory()


def _extract_bearer(authorization: str | None) -> str:
    if not authorization:
        raise UnauthenticatedError()
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthenticatedError()
    return token.strip()


def get_identity_provider(
    session: Annotated[Session, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IdentityProvider:
    return build_identity_adapter(settings, session)


def get_current_user(
    request: Request,
    identity: Annotated[IdentityProvider, Depends(get_identity_provider)],
    authorization: Annotated[str | None, Header()] = None,
) -> User:
    token = _extract_bearer(authorization)
    user = identity.authenticate(token)
    request.state.user_id = str(user.id)
    return user


def get_optional_organization_id(
    x_organization_id: Annotated[str | None, Header(alias="X-Organization-Id")] = None,
) -> UUID | None:
    if x_organization_id is None or x_organization_id == "":
        return None
    try:
        return UUID(x_organization_id)
    except ValueError as exc:
        raise PermissionDeniedError("La organización seleccionada no es válida.") from exc


def get_tenant_context(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db_session)],
    organization_id: Annotated[UUID | None, Depends(get_optional_organization_id)],
) -> TenantContext:
    if organization_id is None:
        raise PermissionDeniedError("Selecciona una organización válida.")
    membership = SqlMembershipRepository(session, organization_id).get_for_user(user.id)
    if membership is None or not membership.is_active():
        raise PermissionDeniedError()
    organization = SqlOrganizationRepository(session).get(organization_id)
    if organization is None:
        raise NotFoundError()
    trace_id = str(getattr(request.state, "trace_id", "unknown"))
    return TenantContext(
        user=user,
        organization_id=organization_id,
        role=membership.role,
        trace_id=trace_id,
    )


def get_organization_service(
    session: Annotated[Session, Depends(get_db_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdFactory, Depends(get_ids)],
) -> OrganizationService:
    return OrganizationService(session, clock, ids)


def get_membership_service(
    session: Annotated[Session, Depends(get_db_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdFactory, Depends(get_ids)],
) -> MembershipService:
    return MembershipService(session, clock, ids)


def get_dimension_service(
    session: Annotated[Session, Depends(get_db_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdFactory, Depends(get_ids)],
) -> DimensionService:
    return DimensionService(session, clock, ids)


def get_budget_version_service(
    session: Annotated[Session, Depends(get_db_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdFactory, Depends(get_ids)],
) -> BudgetVersionService:
    return BudgetVersionService(session, clock, ids)


def get_object_storage(settings: Annotated[Settings, Depends(get_settings)]) -> ObjectStorage:
    return build_object_storage(settings)


def get_import_executor(settings: Annotated[Settings, Depends(get_settings)]) -> ImportExecutor:
    return build_import_runner(settings)


def get_workbook_parser() -> WorkbookParser:
    return build_workbook_parser()


def get_import_service(
    session: Annotated[Session, Depends(get_db_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdFactory, Depends(get_ids)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
    executor: Annotated[ImportExecutor, Depends(get_import_executor)],
    parser: Annotated[WorkbookParser, Depends(get_workbook_parser)],
) -> ImportService:
    return ImportService(session, clock, ids, storage, settings, executor, parser)


def get_analytics_service(
    session: Annotated[Session, Depends(get_db_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdFactory, Depends(get_ids)],
    storage: Annotated[ObjectStorage, Depends(get_object_storage)],
) -> AnalyticsService:
    return AnalyticsService(session, clock, ids, storage)


def get_scenario_service(
    session: Annotated[Session, Depends(get_db_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdFactory, Depends(get_ids)],
) -> ScenarioService:
    return ScenarioService(session, clock, ids)


def get_conversation_service(
    session: Annotated[Session, Depends(get_db_session)],
    clock: Annotated[Clock, Depends(get_clock)],
    ids: Annotated[IdFactory, Depends(get_ids)],
    settings: Annotated[Settings, Depends(get_settings)],
    analytics: Annotated[AnalyticsService, Depends(get_analytics_service)],
    scenarios: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> ConversationService:
    return ConversationService(
        session,
        clock,
        ids,
        settings,
        analytics,
        scenarios,
        build_ai_provider(settings),
    )


DbSession = Annotated[Session, Depends(get_db_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTenant = Annotated[TenantContext, Depends(get_tenant_context)]
OptionalOrgId = Annotated[UUID | None, Depends(get_optional_organization_id)]
SettingsDep = Annotated[Settings, Depends(get_settings)]
OrgServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]
MembershipServiceDep = Annotated[MembershipService, Depends(get_membership_service)]
DimensionServiceDep = Annotated[DimensionService, Depends(get_dimension_service)]
BudgetVersionServiceDep = Annotated[BudgetVersionService, Depends(get_budget_version_service)]
ImportServiceDep = Annotated[ImportService, Depends(get_import_service)]
AnalyticsServiceDep = Annotated[AnalyticsService, Depends(get_analytics_service)]
ScenarioServiceDep = Annotated[ScenarioService, Depends(get_scenario_service)]
ConversationServiceDep = Annotated[ConversationService, Depends(get_conversation_service)]
