from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid5

from sqlalchemy import text

from budgetlens.adapters.db import session_scope
from budgetlens.adapters.persistence.repositories import (
    SqlAccountRepository,
    SqlCostCenterRepository,
    SqlDepartmentRepository,
    SqlMembershipRepository,
    SqlOrganizationRepository,
    SqlUserRepository,
)
from budgetlens.dev_identities import (
    ALPHA_ADMIN_ID,
    ALPHA_ANALYST_ID,
    ALPHA_ORG_ID,
    ALPHA_VIEWER_ID,
    BETA_ADMIN_ID,
    BETA_ANALYST_ID,
    BETA_ORG_ID,
    BOTH_USER_ID,
)
from budgetlens.domain.dimensions import (
    Account,
    CostCenter,
    Department,
    build_unassigned_cost_center,
)
from budgetlens.domain.enums import (
    AccountType,
    DimensionStatus,
    MembershipStatus,
    OrganizationStatus,
    Role,
    UserStatus,
)
from budgetlens.domain.money import Currency
from budgetlens.domain.organization import (
    Membership,
    Organization,
    User,
    normalize_email,
    normalize_name,
    normalize_slug,
)

SEED_NS = UUID("00000000-0000-4000-8000-0000000000aa")


def _stable_id(name: str) -> UUID:
    return uuid5(SEED_NS, name)


def run_seed() -> None:
    now = datetime.now(UTC)
    with session_scope() as session:
        session.execute(
            text(
                """
                INSERT INTO schema_meta (key, value)
                VALUES ('demo_dataset', 'synthetic-local')
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = now()
                """
            )
        )
        users = SqlUserRepository(session)
        orgs = SqlOrganizationRepository(session)

        _upsert_user(
            users,
            User(
                id=ALPHA_ADMIN_ID,
                email=normalize_email("alex.admin@alpha.local"),
                display_name=normalize_name("Alex Admin", field="display_name", max_length=160),
                status=UserStatus.ACTIVE,
                external_subject=None,
                created_at=now,
                updated_at=now,
            ),
        )
        _upsert_user(
            users,
            User(
                id=ALPHA_ANALYST_ID,
                email="ana.analyst@alpha.local",
                display_name="Ana Analyst",
                status=UserStatus.ACTIVE,
                external_subject=None,
                created_at=now,
                updated_at=now,
            ),
        )
        _upsert_user(
            users,
            User(
                id=ALPHA_VIEWER_ID,
                email="vic.viewer@alpha.local",
                display_name="Vic Viewer",
                status=UserStatus.ACTIVE,
                external_subject=None,
                created_at=now,
                updated_at=now,
            ),
        )
        _upsert_user(
            users,
            User(
                id=BETA_ADMIN_ID,
                email="bea.admin@beta.local",
                display_name="Bea Admin",
                status=UserStatus.ACTIVE,
                external_subject=None,
                created_at=now,
                updated_at=now,
            ),
        )
        _upsert_user(
            users,
            User(
                id=BETA_ANALYST_ID,
                email="ben.analyst@beta.local",
                display_name="Ben Analyst",
                status=UserStatus.ACTIVE,
                external_subject=None,
                created_at=now,
                updated_at=now,
            ),
        )
        _upsert_user(
            users,
            User(
                id=BOTH_USER_ID,
                email="pat.both@budgetlens.local",
                display_name="Pat Dual",
                status=UserStatus.ACTIVE,
                external_subject=None,
                created_at=now,
                updated_at=now,
            ),
        )

        alpha = Organization(
            id=ALPHA_ORG_ID,
            name="Alpha",
            slug=normalize_slug("alpha"),
            functional_currency=Currency("MXN"),
            fiscal_year_start_month=1,
            status=OrganizationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            version=1,
        )
        beta = Organization(
            id=BETA_ORG_ID,
            name="Beta",
            slug=normalize_slug("beta"),
            functional_currency=Currency("USD"),
            fiscal_year_start_month=4,
            status=OrganizationStatus.ACTIVE,
            created_at=now,
            updated_at=now,
            version=1,
        )
        _upsert_org(orgs, alpha)
        _upsert_org(orgs, beta)
        session.flush()

        _seed_org(
            session,
            organization=alpha,
            members=[
                (ALPHA_ADMIN_ID, Role.ADMIN),
                (ALPHA_ANALYST_ID, Role.ANALYST),
                (ALPHA_VIEWER_ID, Role.VIEWER),
                (BOTH_USER_ID, Role.ANALYST),
            ],
            now=now,
        )
        _seed_org(
            session,
            organization=beta,
            members=[
                (BETA_ADMIN_ID, Role.ADMIN),
                (BETA_ANALYST_ID, Role.ANALYST),
                (BOTH_USER_ID, Role.VIEWER),
            ],
            now=now,
        )


def _upsert_user(users: SqlUserRepository, user: User) -> None:
    existing = users.get(user.id) or users.get_by_email(user.email)
    if existing is None:
        users.add(user)
        return
    users.save(
        User(
            id=existing.id,
            email=user.email,
            display_name=user.display_name,
            status=user.status,
            external_subject=existing.external_subject,
            created_at=existing.created_at,
            updated_at=user.updated_at,
        )
    )


def _upsert_org(orgs: SqlOrganizationRepository, organization: Organization) -> None:
    existing = orgs.get(organization.id) or orgs.get_by_slug(organization.slug)
    if existing is None:
        orgs.add(organization)
        return
    orgs.save(
        Organization(
            id=existing.id,
            name=organization.name,
            slug=organization.slug,
            functional_currency=organization.functional_currency,
            fiscal_year_start_month=organization.fiscal_year_start_month,
            status=organization.status,
            created_at=existing.created_at,
            updated_at=organization.updated_at,
            version=existing.version,
        )
    )


def _seed_org(
    session: object,
    *,
    organization: Organization,
    members: list[tuple[UUID, Role]],
    now: datetime,
) -> None:
    from sqlalchemy.orm import Session

    assert isinstance(session, Session)
    memberships = SqlMembershipRepository(session, organization.id)
    accounts = SqlAccountRepository(session, organization.id)
    departments = SqlDepartmentRepository(session, organization.id)
    cost_centers = SqlCostCenterRepository(session, organization.id)

    for user_id, role in members:
        current = memberships.get_for_user(user_id)
        if current is None:
            memberships.add(
                Membership(
                    id=_stable_id(f"membership:{organization.slug}:{user_id}"),
                    organization_id=organization.id,
                    user_id=user_id,
                    role=role,
                    status=MembershipStatus.ACTIVE,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            memberships.save(
                current.with_updates(now=now, role=role, status=MembershipStatus.ACTIVE)
            )

    if cost_centers.get_by_code("UNASSIGNED") is None:
        cost_centers.add(
            build_unassigned_cost_center(
                organization_id=organization.id,
                cost_center_id=_stable_id(f"cc:{organization.slug}:UNASSIGNED"),
                now=now,
            )
        )

    if departments.get_by_code("FIN") is None:
        departments.add(
            Department(
                id=_stable_id(f"dept:{organization.slug}:FIN"),
                organization_id=organization.id,
                code="FIN",
                name="Finanzas",
                status=DimensionStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
    if departments.get_by_code("OPS") is None:
        departments.add(
            Department(
                id=_stable_id(f"dept:{organization.slug}:OPS"),
                organization_id=organization.id,
                code="OPS",
                name="Operaciones",
                status=DimensionStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )

    if accounts.get_by_code("4000") is None:
        accounts.add(
            Account(
                id=_stable_id(f"acct:{organization.slug}:4000"),
                organization_id=organization.id,
                code="4000",
                name="Ingresos",
                account_type=AccountType.REVENUE,
                parent_id=None,
                status=DimensionStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
    if accounts.get_by_code("6100") is None:
        accounts.add(
            Account(
                id=_stable_id(f"acct:{organization.slug}:6100"),
                organization_id=organization.id,
                code="6100",
                name="Servicios externos",
                account_type=AccountType.EXPENSE,
                parent_id=None,
                status=DimensionStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
    if cost_centers.get_by_code("CC-GEN") is None:
        cost_centers.add(
            CostCenter(
                id=_stable_id(f"cc:{organization.slug}:CC-GEN"),
                organization_id=organization.id,
                code="CC-GEN",
                name="General",
                status=DimensionStatus.ACTIVE,
                created_at=now,
                updated_at=now,
            )
        )
