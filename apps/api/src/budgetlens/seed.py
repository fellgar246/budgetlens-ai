from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid5

from sqlalchemy import text

from budgetlens.adapters.db import session_scope
from budgetlens.adapters.persistence.finance_repositories import (
    SqlFinancialEntryRepository,
    SqlImportJobRepository,
)
from budgetlens.adapters.persistence.repositories import (
    SqlAccountRepository,
    SqlAuditRepository,
    SqlBudgetVersionRepository,
    SqlCostCenterRepository,
    SqlDepartmentRepository,
    SqlMembershipRepository,
    SqlOrganizationRepository,
    SqlUserRepository,
)
from budgetlens.application.ai_eval_dataset import (
    EVAL_BUDGET_VERSION_NAME,
    seed_ledger_rows,
)
from budgetlens.application.audit import record_audit
from budgetlens.config import get_settings
from budgetlens.dev_identities import (
    ALPHA_ADMIN_ID,
    ALPHA_ANALYST_ID,
    ALPHA_ORG_ID,
    ALPHA_VIEWER_ID,
    BETA_ADMIN_ID,
    BETA_ANALYST_ID,
    BETA_ORG_ID,
    BOTH_USER_ID,
    OPERATOR_ID,
)
from budgetlens.domain.audit import ACTOR_SYSTEM, DEMO_SEEDED, SYSTEM_SEED
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
    PlatformRole,
    Role,
    UserStatus,
)
from budgetlens.domain.identities import SystemClock, Uuid4Factory
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
ALLOWED_SEED_ENVIRONMENTS = frozenset({"local", "test", "dev"})
DEMO_ORGANIZATION_SLUGS = frozenset({"alpha", "beta"})
DEMO_USER_EMAILS = frozenset(
    {
        "alex.admin@alpha.local",
        "ana.analyst@alpha.local",
        "vic.viewer@alpha.local",
        "bea.admin@beta.local",
        "ben.analyst@beta.local",
        "pat.both@budgetlens.local",
        "oli.operator@platform.local",
    }
)


def _stable_id(name: str) -> UUID:
    return uuid5(SEED_NS, name)


def assert_seed_allowed(app_env: str) -> None:
    if app_env == "prod":
        raise ValueError("Seed is refused in production")
    if app_env not in ALLOWED_SEED_ENVIRONMENTS:
        raise ValueError("Seed requires APP_ENV=local, test, or dev")


def demo_dataset_label(app_env: str) -> str:
    return "synthetic-demo" if app_env == "dev" else "synthetic-local"


def run_seed(*, include_financials: bool = False) -> None:
    settings = get_settings()
    assert_seed_allowed(settings.app_env)
    now = datetime.now(UTC)
    dataset = demo_dataset_label(settings.app_env)
    with session_scope() as session:
        session.execute(
            text(
                """
                INSERT INTO schema_meta (key, value)
                VALUES ('demo_dataset', :dataset)
                ON CONFLICT (key) DO UPDATE
                SET value = EXCLUDED.value, updated_at = now()
                """
            ),
            {"dataset": dataset},
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
        _upsert_user(
            users,
            User(
                id=OPERATOR_ID,
                email="oli.operator@platform.local",
                display_name="Oli Operator",
                status=UserStatus.ACTIVE,
                external_subject=None,
                created_at=now,
                updated_at=now,
                platform_role=PlatformRole.OPERATOR,
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
        if frozenset({alpha.slug, beta.slug}) != DEMO_ORGANIZATION_SLUGS:
            raise ValueError("Seed may only create known demo organizations")
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
        if include_financials:
            _seed_financials(
                session,
                organization=alpha,
                created_by=ALPHA_ADMIN_ID,
                now=now,
            )
            _seed_financials(
                session,
                organization=beta,
                created_by=BETA_ADMIN_ID,
                now=now,
            )
        record_audit(
            SqlAuditRepository(session),
            clock=SystemClock(),
            ids=Uuid4Factory(),
            organization_id=None,
            actor_id=None,
            actor_type=ACTOR_SYSTEM,
            actor_ref=SYSTEM_SEED,
            action=DEMO_SEEDED,
            resource_type="demo",
            resource_id=_stable_id("demo-dataset"),
            trace_id="seed-demo",
            metadata={
                "dataset": dataset,
                "organizations": sorted(DEMO_ORGANIZATION_SLUGS),
                "include_financials": include_financials,
            },
            outcome="success",
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
            platform_role=user.platform_role,
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
            conversation_retention_days=existing.conversation_retention_days,
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
    extra_departments = (
        ("SALES", "Sales"),
        ("PEO", "People"),
    )
    for code, name in extra_departments:
        if departments.get_by_code(code) is None:
            departments.add(
                Department(
                    id=_stable_id(f"dept:{organization.slug}:{code}"),
                    organization_id=organization.id,
                    code=code,
                    name=name,
                    status=DimensionStatus.ACTIVE,
                    created_at=now,
                    updated_at=now,
                )
            )
    extra_accounts = (
        ("4100", "Revenue", AccountType.REVENUE),
        ("6110", "Maintenance", AccountType.EXPENSE),
        ("6120", "Contractors", AccountType.EXPENSE),
        ("6200", "Payroll", AccountType.EXPENSE),
        ("6300", "Emergency", AccountType.EXPENSE),
        ("6400", "Unused", AccountType.EXPENSE),
    )
    for code, name, account_type in extra_accounts:
        if accounts.get_by_code(code) is None:
            accounts.add(
                Account(
                    id=_stable_id(f"acct:{organization.slug}:{code}"),
                    organization_id=organization.id,
                    code=code,
                    name=name,
                    account_type=account_type,
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


def _seed_financials(
    session: object,
    *,
    organization: Organization,
    created_by: UUID,
    now: datetime,
) -> None:
    from sqlalchemy.orm import Session

    from budgetlens.domain.budget_version import BudgetVersion
    from budgetlens.domain.enums import BudgetVersionStatus, ScenarioType

    assert isinstance(session, Session)
    versions = SqlBudgetVersionRepository(session, organization.id)
    fiscal_year = 2026 if organization.fiscal_year_start_month == 1 else 2027
    version_name = EVAL_BUDGET_VERSION_NAME
    version_id = _stable_id(f"version:{organization.slug}:{fiscal_year}")
    existing = versions.get(version_id) or versions.get_by_name(fiscal_year, version_name)
    if existing is not None:
        return

    version = BudgetVersion(
        id=version_id,
        organization_id=organization.id,
        name=version_name,
        fiscal_year=fiscal_year,
        status=BudgetVersionStatus.PUBLISHED,
        is_active=True,
        published_at=now,
        published_by=created_by,
        created_at=now,
        version=1,
    )
    versions.add(version)
    session.flush()

    accounts = SqlAccountRepository(session, organization.id)
    departments = SqlDepartmentRepository(session, organization.id)
    cost_centers = SqlCostCenterRepository(session, organization.id)
    jobs = SqlImportJobRepository(session, organization.id)
    entries = SqlFinancialEntryRepository(session, organization.id)

    account_ids = {
        code: accounts.get_by_code(code).id  # type: ignore[union-attr]
        for code in ("4100", "6110", "6120", "6200", "6300", "6400")
    }
    department_ids = {
        code: departments.get_by_code(code).id  # type: ignore[union-attr]
        for code in ("SALES", "OPS", "PEO")
    }
    cost_center_ids = {
        code: cost_centers.get_by_code(code).id  # type: ignore[union-attr]
        for code in ("CC-GEN", "UNASSIGNED")
    }

    currency = organization.functional_currency
    budget_rows, actual_rows = seed_ledger_rows(
        january_start=organization.fiscal_year_start_month == 1
    )
    _add_seed_import(
        session,
        jobs,
        entries,
        organization=organization,
        created_by=created_by,
        now=now,
        import_type=ScenarioType.BUDGET,
        version_id=version.id,
        filename=f"{organization.slug}-budget-seed.csv",
        rows=budget_rows,
        account_ids=account_ids,
        department_ids=department_ids,
        cost_center_ids=cost_center_ids,
        currency=currency,
        fiscal_year=fiscal_year,
    )
    _add_seed_import(
        session,
        jobs,
        entries,
        organization=organization,
        created_by=created_by,
        now=now,
        import_type=ScenarioType.ACTUAL,
        version_id=None,
        filename=f"{organization.slug}-actuals-seed.csv",
        rows=actual_rows,
        account_ids=account_ids,
        department_ids=department_ids,
        cost_center_ids=cost_center_ids,
        currency=currency,
        fiscal_year=fiscal_year,
    )


def _add_seed_import(
    session: object,
    jobs: SqlImportJobRepository,
    entries: SqlFinancialEntryRepository,
    *,
    organization: Organization,
    created_by: UUID,
    now: datetime,
    import_type: object,
    version_id: UUID | None,
    filename: str,
    rows: tuple[tuple[date, str, str, str, Decimal], ...],
    account_ids: dict[str, UUID],
    department_ids: dict[str, UUID],
    cost_center_ids: dict[str, UUID],
    currency: object,
    fiscal_year: int,
) -> None:
    from sqlalchemy.orm import Session

    from budgetlens.domain.enums import ImportJobStatus, ScenarioType
    from budgetlens.domain.financial_entry import FinancialEntry
    from budgetlens.domain.importing import ImportJob
    from budgetlens.domain.money import Currency, MoneyAmount

    assert isinstance(session, Session)
    assert isinstance(import_type, ScenarioType)
    assert isinstance(currency, Currency)
    job_id = _stable_id(f"job:{organization.slug}:{import_type.value}:{fiscal_year}")
    total = sum((amount for *_rest, amount in rows), Decimal("0"))
    jobs.add(
        ImportJob(
            id=job_id,
            organization_id=organization.id,
            created_by=created_by,
            import_type=import_type,
            budget_version_id=version_id,
            status=ImportJobStatus.APPLIED,
            original_filename=filename,
            object_key=f"seed/{organization.slug}/{filename}",
            sha256="a" * 64,
            size_bytes=256,
            media_type="text/csv",
            template_version="1.0",
            mapping_json={"columns": {}},
            row_count=len(rows),
            valid_count=len(rows),
            error_count=0,
            warning_count=0,
            period_min=min(period for period, *_rest in rows),
            period_max=max(period for period, *_rest in rows),
            valid_amount_total=f"{total:.4f}",
            idempotency_fingerprint=None,
            started_at=now,
            completed_at=now,
            created_at=now,
            failure_code=None,
            create_missing_dimensions=False,
            sheet_name=None,
        )
    )
    session.flush()
    for index, (period, account, department, cost_center, amount) in enumerate(rows, start=2):
        entries.add(
            FinancialEntry(
                id=_stable_id(f"entry:{job_id}:{index}"),
                organization_id=organization.id,
                import_job_id=job_id,
                scenario_type=import_type,
                budget_version_id=version_id,
                period_start=period,
                fiscal_year=organization.period_for(period).fiscal_year,
                account_id=account_ids[account],
                department_id=department_ids[department],
                cost_center_id=cost_center_ids[cost_center],
                amount=MoneyAmount(amount),
                currency=currency,
                source_row_number=index,
                source_reference=None,
                created_at=now,
            )
        )
