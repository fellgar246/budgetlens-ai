from __future__ import annotations

from fastapi import APIRouter

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
    repository = SqlUserRepository(session)
    users = repository.list_all()
    items: list[DevIdentity] = []
    for user in users:
        memberships = repository.list_memberships_with_organizations(user.id)
        items.append(
            DevIdentity(
                id=user.id,
                email=user.email,
                display_name=user.display_name,
                platform_role=user.platform_role.value if user.platform_role else None,
                memberships=[
                    DevMembership(
                        organization_id=organization.id,
                        organization_name=organization.name,
                        role=membership.role.value,
                    )
                    for membership, organization in memberships
                ],
            )
        )
    return DevIdentityListResponse(users=items)
