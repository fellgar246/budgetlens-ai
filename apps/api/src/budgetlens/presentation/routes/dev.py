from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from budgetlens.adapters.persistence.models import MembershipRow, OrganizationRow
from budgetlens.adapters.persistence.repositories import SqlUserRepository
from budgetlens.domain.errors import NotFoundError
from budgetlens.presentation.deps import DbSession, SettingsDep
from budgetlens.presentation.schemas import DevIdentity, DevIdentityListResponse, DevMembership

router = APIRouter(tags=["dev"])


@router.get(
    "/dev/identities",
    response_model=DevIdentityListResponse,
    operation_id="list_dev_identities",
)
def list_dev_identities(settings: SettingsDep, session: DbSession) -> DevIdentityListResponse:
    if settings.auth_mode != "dev" or settings.app_env not in {"local", "test"}:
        raise NotFoundError()
    users = SqlUserRepository(session).list_all()
    items: list[DevIdentity] = []
    for user in users:
        rows = session.execute(
            select(MembershipRow, OrganizationRow)
            .join(OrganizationRow, OrganizationRow.id == MembershipRow.organization_id)
            .where(MembershipRow.user_id == user.id)
            .order_by(OrganizationRow.name)
        ).all()
        items.append(
            DevIdentity(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                platform_role=user.platform_role.value if user.platform_role else None,
                memberships=[
                    DevMembership(
                        organization_id=org.id,
                        organization_name=org.name,
                        role=membership.role,
                    )
                    for membership, org in rows
                ],
            )
        )
    return DevIdentityListResponse(users=items)
