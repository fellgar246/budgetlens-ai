from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.mapping import (
    account_from_row,
    apply_account,
    apply_audit,
    apply_budget_version,
    apply_cost_center,
    apply_department,
    apply_membership,
    apply_organization,
    apply_user,
    audit_from_row,
    budget_version_from_row,
    cost_center_from_row,
    department_from_row,
    membership_from_row,
    organization_from_row,
    user_from_row,
)
from budgetlens.adapters.persistence.models import (
    AccountRow,
    AuditEventRow,
    BudgetVersionRow,
    CostCenterRow,
    DepartmentRow,
    IdempotencyRecordRow,
    MembershipRow,
    OrganizationRow,
    UserRow,
)
from budgetlens.application.pagination import Page, decode_cursor, encode_cursor
from budgetlens.domain.audit import AuditEvent
from budgetlens.domain.budget_version import BudgetVersion
from budgetlens.domain.dimensions import Account, CostCenter, Department
from budgetlens.domain.enums import BudgetVersionStatus, MembershipStatus
from budgetlens.domain.organization import Membership, Organization, User


class SqlUserRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: UUID) -> User | None:
        row = self._session.get(UserRow, user_id)
        return user_from_row(row) if row else None

    def get_by_email(self, email: str) -> User | None:
        row = self._session.scalar(
            select(UserRow).where(func.lower(UserRow.email) == email.lower())
        )
        return user_from_row(row) if row else None

    def get_by_external_subject(self, subject: str) -> User | None:
        row = self._session.scalar(select(UserRow).where(UserRow.external_subject == subject))
        return user_from_row(row) if row else None

    def add(self, user: User) -> None:
        row = UserRow()
        apply_user(row, user)
        self._session.add(row)

    def save(self, user: User) -> None:
        row = self._session.get(UserRow, user.id)
        if row is None:
            self.add(user)
            return
        apply_user(row, user)

    def list_all(self) -> list[User]:
        rows = self._session.scalars(select(UserRow).order_by(UserRow.email, UserRow.id)).all()
        return [user_from_row(row) for row in rows]

    def list_memberships_with_organizations(
        self, user_id: UUID
    ) -> list[tuple[Membership, Organization]]:
        rows = self._session.execute(
            select(MembershipRow, OrganizationRow)
            .join(OrganizationRow, OrganizationRow.id == MembershipRow.organization_id)
            .where(MembershipRow.user_id == user_id)
            .order_by(OrganizationRow.name, OrganizationRow.id)
        ).all()
        return [
            (membership_from_row(membership), organization_from_row(organization))
            for membership, organization in rows
        ]


class SqlOrganizationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, organization_id: UUID) -> Organization | None:
        row = self._session.get(OrganizationRow, organization_id)
        return organization_from_row(row) if row else None

    def get_by_slug(self, slug: str) -> Organization | None:
        row = self._session.scalar(select(OrganizationRow).where(OrganizationRow.slug == slug))
        return organization_from_row(row) if row else None

    def add(self, organization: Organization) -> None:
        row = OrganizationRow()
        apply_organization(row, organization)
        self._session.add(row)

    def save(self, organization: Organization) -> None:
        row = self._session.get(OrganizationRow, organization.id)
        if row is None:
            self.add(organization)
            return
        apply_organization(row, organization)

    def list_for_user(
        self,
        user_id: UUID,
        *,
        cursor: str | None,
        limit: int,
    ) -> Page[tuple[Organization, Membership]]:
        stmt = (
            select(OrganizationRow, MembershipRow)
            .join(MembershipRow, MembershipRow.organization_id == OrganizationRow.id)
            .where(
                MembershipRow.user_id == user_id,
                MembershipRow.status == MembershipStatus.ACTIVE.value,
            )
            .order_by(OrganizationRow.created_at, OrganizationRow.id)
        )
        parsed = decode_cursor(cursor)
        if parsed is not None:
            created_at = datetime.fromisoformat(parsed["created_at"])
            last_id = UUID(parsed["id"])
            stmt = stmt.where(
                or_(
                    OrganizationRow.created_at > created_at,
                    and_(OrganizationRow.created_at == created_at, OrganizationRow.id > last_id),
                )
            )
        rows = self._session.execute(stmt.limit(limit + 1)).all()
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        items = [(organization_from_row(org), membership_from_row(mem)) for org, mem in page_rows]
        next_cursor = None
        if has_more and page_rows:
            last_org = page_rows[-1][0]
            next_cursor = encode_cursor(
                {"created_at": last_org.created_at.isoformat(), "id": str(last_org.id)}
            )
        return Page(items=items, next_cursor=next_cursor, has_more=has_more)


class SqlMembershipRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = organization_id

    def get(self, membership_id: UUID) -> Membership | None:
        row = self._session.get(MembershipRow, membership_id)
        if row is None or row.organization_id != self._organization_id:
            return None
        return membership_from_row(row)

    def get_for_user(self, user_id: UUID) -> Membership | None:
        row = self._session.scalar(
            select(MembershipRow).where(
                MembershipRow.organization_id == self._organization_id,
                MembershipRow.user_id == user_id,
            )
        )
        return membership_from_row(row) if row else None

    def list_active_admins(self) -> list[Membership]:
        rows = self._session.scalars(
            select(MembershipRow).where(
                MembershipRow.organization_id == self._organization_id,
                MembershipRow.role == "admin",
                MembershipRow.status == MembershipStatus.ACTIVE.value,
            )
        ).all()
        return [membership_from_row(row) for row in rows]

    def add(self, membership: Membership) -> None:
        row = MembershipRow()
        apply_membership(row, membership)
        self._session.add(row)

    def save(self, membership: Membership) -> None:
        row = self._session.get(MembershipRow, membership.id)
        if row is None or row.organization_id != self._organization_id:
            self.add(membership)
            return
        apply_membership(row, membership)

    def list_page(self, *, cursor: str | None, limit: int) -> Page[Membership]:
        stmt = (
            select(MembershipRow)
            .where(MembershipRow.organization_id == self._organization_id)
            .order_by(MembershipRow.created_at, MembershipRow.id)
        )
        parsed = decode_cursor(cursor)
        if parsed is not None:
            created_at = datetime.fromisoformat(parsed["created_at"])
            last_id = UUID(parsed["id"])
            stmt = stmt.where(
                or_(
                    MembershipRow.created_at > created_at,
                    and_(MembershipRow.created_at == created_at, MembershipRow.id > last_id),
                )
            )
        rows = list(self._session.scalars(stmt.limit(limit + 1)).all())
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor(
                {"created_at": last.created_at.isoformat(), "id": str(last.id)}
            )
        return Page(
            items=[membership_from_row(row) for row in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )


class SqlAccountRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = organization_id

    def get(self, account_id: UUID) -> Account | None:
        row = self._session.get(AccountRow, account_id)
        if row is None or row.organization_id != self._organization_id:
            return None
        return account_from_row(row)

    def get_by_code(self, code: str) -> Account | None:
        row = self._session.scalar(
            select(AccountRow).where(
                AccountRow.organization_id == self._organization_id,
                AccountRow.code == code,
            )
        )
        return account_from_row(row) if row else None

    def add(self, account: Account) -> None:
        row = AccountRow()
        apply_account(row, account)
        self._session.add(row)

    def save(self, account: Account) -> None:
        row = self._session.get(AccountRow, account.id)
        if row is None or row.organization_id != self._organization_id:
            self.add(account)
            return
        apply_account(row, account)

    def ancestor_ids(self, parent_id: UUID | None) -> list[UUID]:
        chain: list[UUID] = []
        current = parent_id
        seen: set[UUID] = set()
        while current is not None:
            if current in seen:
                chain.append(current)
                break
            seen.add(current)
            row = self._session.get(AccountRow, current)
            if row is None or row.organization_id != self._organization_id:
                break
            chain.append(row.id)
            current = row.parent_id
        return chain

    def list_page(
        self,
        *,
        cursor: str | None,
        limit: int,
        status: str | None,
        search: str | None,
    ) -> Page[Account]:
        stmt = select(AccountRow).where(AccountRow.organization_id == self._organization_id)
        if status is not None:
            stmt = stmt.where(AccountRow.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(or_(AccountRow.code.ilike(pattern), AccountRow.name.ilike(pattern)))
        stmt = stmt.order_by(AccountRow.code, AccountRow.id)
        parsed = decode_cursor(cursor)
        if parsed is not None:
            stmt = stmt.where(
                or_(
                    AccountRow.code > parsed["code"],
                    and_(AccountRow.code == parsed["code"], AccountRow.id > UUID(parsed["id"])),
                )
            )
        rows = list(self._session.scalars(stmt.limit(limit + 1)).all())
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor({"code": last.code, "id": str(last.id)})
        return Page(
            items=[account_from_row(row) for row in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )


class SqlDepartmentRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = organization_id

    def get(self, department_id: UUID) -> Department | None:
        row = self._session.get(DepartmentRow, department_id)
        if row is None or row.organization_id != self._organization_id:
            return None
        return department_from_row(row)

    def get_by_code(self, code: str) -> Department | None:
        row = self._session.scalar(
            select(DepartmentRow).where(
                DepartmentRow.organization_id == self._organization_id,
                DepartmentRow.code == code,
            )
        )
        return department_from_row(row) if row else None

    def add(self, department: Department) -> None:
        row = DepartmentRow()
        apply_department(row, department)
        self._session.add(row)

    def save(self, department: Department) -> None:
        row = self._session.get(DepartmentRow, department.id)
        if row is None or row.organization_id != self._organization_id:
            self.add(department)
            return
        apply_department(row, department)

    def list_page(
        self,
        *,
        cursor: str | None,
        limit: int,
        status: str | None,
        search: str | None,
    ) -> Page[Department]:
        stmt = select(DepartmentRow).where(DepartmentRow.organization_id == self._organization_id)
        if status is not None:
            stmt = stmt.where(DepartmentRow.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(DepartmentRow.code.ilike(pattern), DepartmentRow.name.ilike(pattern))
            )
        stmt = stmt.order_by(DepartmentRow.code, DepartmentRow.id)
        parsed = decode_cursor(cursor)
        if parsed is not None:
            stmt = stmt.where(
                or_(
                    DepartmentRow.code > parsed["code"],
                    and_(
                        DepartmentRow.code == parsed["code"],
                        DepartmentRow.id > UUID(parsed["id"]),
                    ),
                )
            )
        rows = list(self._session.scalars(stmt.limit(limit + 1)).all())
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor({"code": last.code, "id": str(last.id)})
        return Page(
            items=[department_from_row(row) for row in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )


class SqlCostCenterRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = organization_id

    def get(self, cost_center_id: UUID) -> CostCenter | None:
        row = self._session.get(CostCenterRow, cost_center_id)
        if row is None or row.organization_id != self._organization_id:
            return None
        return cost_center_from_row(row)

    def get_by_code(self, code: str) -> CostCenter | None:
        row = self._session.scalar(
            select(CostCenterRow).where(
                CostCenterRow.organization_id == self._organization_id,
                CostCenterRow.code == code,
            )
        )
        return cost_center_from_row(row) if row else None

    def add(self, cost_center: CostCenter) -> None:
        row = CostCenterRow()
        apply_cost_center(row, cost_center)
        self._session.add(row)

    def save(self, cost_center: CostCenter) -> None:
        row = self._session.get(CostCenterRow, cost_center.id)
        if row is None or row.organization_id != self._organization_id:
            self.add(cost_center)
            return
        apply_cost_center(row, cost_center)

    def list_page(
        self,
        *,
        cursor: str | None,
        limit: int,
        status: str | None,
        search: str | None,
    ) -> Page[CostCenter]:
        stmt = select(CostCenterRow).where(CostCenterRow.organization_id == self._organization_id)
        if status is not None:
            stmt = stmt.where(CostCenterRow.status == status)
        if search:
            pattern = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(CostCenterRow.code.ilike(pattern), CostCenterRow.name.ilike(pattern))
            )
        stmt = stmt.order_by(CostCenterRow.code, CostCenterRow.id)
        parsed = decode_cursor(cursor)
        if parsed is not None:
            stmt = stmt.where(
                or_(
                    CostCenterRow.code > parsed["code"],
                    and_(
                        CostCenterRow.code == parsed["code"],
                        CostCenterRow.id > UUID(parsed["id"]),
                    ),
                )
            )
        rows = list(self._session.scalars(stmt.limit(limit + 1)).all())
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor({"code": last.code, "id": str(last.id)})
        return Page(
            items=[cost_center_from_row(row) for row in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )


class SqlBudgetVersionRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = organization_id

    def get(self, version_id: UUID) -> BudgetVersion | None:
        row = self._session.get(BudgetVersionRow, version_id)
        if row is None or row.organization_id != self._organization_id:
            return None
        return budget_version_from_row(row)

    def get_by_name(self, fiscal_year: int, name: str) -> BudgetVersion | None:
        row = self._session.scalar(
            select(BudgetVersionRow).where(
                BudgetVersionRow.organization_id == self._organization_id,
                BudgetVersionRow.fiscal_year == fiscal_year,
                BudgetVersionRow.name == name,
            )
        )
        return budget_version_from_row(row) if row else None

    def get_active(self, fiscal_year: int) -> BudgetVersion | None:
        row = self._session.scalar(
            select(BudgetVersionRow).where(
                BudgetVersionRow.organization_id == self._organization_id,
                BudgetVersionRow.fiscal_year == fiscal_year,
                BudgetVersionRow.is_active.is_(True),
                BudgetVersionRow.status == BudgetVersionStatus.PUBLISHED.value,
            )
        )
        return budget_version_from_row(row) if row else None

    def add(self, version: BudgetVersion) -> None:
        row = BudgetVersionRow()
        apply_budget_version(row, version)
        self._session.add(row)

    def save(self, version: BudgetVersion) -> None:
        row = self._session.get(BudgetVersionRow, version.id)
        if row is None or row.organization_id != self._organization_id:
            self.add(version)
            return
        apply_budget_version(row, version)

    def list_page(
        self,
        *,
        cursor: str | None,
        limit: int,
        fiscal_year: int | None,
        include_archived: bool,
    ) -> Page[BudgetVersion]:
        stmt = select(BudgetVersionRow).where(
            BudgetVersionRow.organization_id == self._organization_id
        )
        if fiscal_year is not None:
            stmt = stmt.where(BudgetVersionRow.fiscal_year == fiscal_year)
        if not include_archived:
            stmt = stmt.where(BudgetVersionRow.status != BudgetVersionStatus.ARCHIVED.value)
        stmt = stmt.order_by(
            BudgetVersionRow.fiscal_year, BudgetVersionRow.name, BudgetVersionRow.id
        )
        parsed = decode_cursor(cursor)
        if parsed is not None:
            stmt = stmt.where(
                or_(
                    BudgetVersionRow.fiscal_year > int(parsed["fiscal_year"]),
                    and_(
                        BudgetVersionRow.fiscal_year == int(parsed["fiscal_year"]),
                        BudgetVersionRow.name > parsed["name"],
                    ),
                    and_(
                        BudgetVersionRow.fiscal_year == int(parsed["fiscal_year"]),
                        BudgetVersionRow.name == parsed["name"],
                        BudgetVersionRow.id > UUID(parsed["id"]),
                    ),
                )
            )
        rows = self._session.scalars(stmt.limit(limit + 1)).all()
        has_more = len(rows) > limit
        page_rows = list(rows[:limit])
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor(
                {"fiscal_year": str(last.fiscal_year), "name": last.name, "id": str(last.id)}
            )
        return Page(
            items=[budget_version_from_row(row) for row in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )


class SqlAuditRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: AuditEvent) -> None:
        row = AuditEventRow()
        apply_audit(row, event)
        self._session.add(row)

    def list_for_resource(self, resource_id: UUID) -> list[AuditEvent]:
        rows = self._session.scalars(
            select(AuditEventRow)
            .where(AuditEventRow.resource_id == resource_id)
            .order_by(AuditEventRow.created_at)
        ).all()
        return [audit_from_row(row) for row in rows]

    def list_page(
        self,
        *,
        organization_id: UUID,
        cursor: str | None,
        limit: int,
        action: str | None = None,
        actor_id: UUID | None = None,
        resource_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Page[AuditEvent]:
        stmt = select(AuditEventRow).where(AuditEventRow.organization_id == organization_id)
        if action:
            stmt = stmt.where(AuditEventRow.action == action)
        if actor_id:
            stmt = stmt.where(AuditEventRow.actor_id == actor_id)
        if resource_type:
            stmt = stmt.where(AuditEventRow.resource_type == resource_type)
        if date_from:
            stmt = stmt.where(AuditEventRow.created_at >= date_from)
        if date_to:
            stmt = stmt.where(AuditEventRow.created_at <= date_to)
        stmt = stmt.order_by(AuditEventRow.created_at.desc(), AuditEventRow.id.desc())
        parsed = decode_cursor(cursor)
        if parsed is not None:
            created_at = datetime.fromisoformat(parsed["created_at"])
            last_id = UUID(parsed["id"])
            stmt = stmt.where(
                or_(
                    AuditEventRow.created_at < created_at,
                    and_(AuditEventRow.created_at == created_at, AuditEventRow.id < last_id),
                )
            )
        rows = list(self._session.scalars(stmt.limit(limit + 1)).all())
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        next_cursor = None
        if has_more and page_rows:
            last = page_rows[-1]
            next_cursor = encode_cursor(
                {"created_at": last.created_at.isoformat(), "id": str(last.id)}
            )
        return Page(
            items=[audit_from_row(row) for row in page_rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )


class SqlIdempotencyRepository:
    def __init__(self, session: Session, organization_id: UUID) -> None:
        self._session = session
        self._organization_id = organization_id

    def get(self, *, user_id: UUID, operation: str, key: str) -> IdempotencyRecordRow | None:
        return self._session.scalar(
            select(IdempotencyRecordRow).where(
                IdempotencyRecordRow.organization_id == self._organization_id,
                IdempotencyRecordRow.user_id == user_id,
                IdempotencyRecordRow.operation == operation,
                IdempotencyRecordRow.key == key,
            )
        )

    def add(self, row: IdempotencyRecordRow) -> None:
        self._session.add(row)
