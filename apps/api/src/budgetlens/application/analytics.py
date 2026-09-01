from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import Select, and_, case, func, literal, or_, select
from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.finance_repositories import SqlExportJobRepository
from budgetlens.adapters.persistence.models import (
    AccountRow,
    CostCenterRow,
    DepartmentRow,
    FinancialEntryRow,
)
from budgetlens.adapters.persistence.repositories import (
    SqlAuditRepository,
    SqlBudgetVersionRepository,
    SqlOrganizationRepository,
)
from budgetlens.application.audit import record_audit
from budgetlens.application.context import TenantContext
from budgetlens.application.pagination import Page, clamp_limit, decode_cursor, encode_cursor
from budgetlens.application.rate_limit import enforce_limit
from budgetlens.config import get_settings
from budgetlens.domain.enums import (
    AccountType,
    AnalyticsGroupBy,
    AnalyticsSort,
    ExportJobStatus,
    ExportType,
    Permission,
    SortDirection,
)
from budgetlens.domain.errors import NotFoundError, ValidationError, field_issue
from budgetlens.domain.exporting import ExportJob, export_filename, render_csv
from budgetlens.domain.identities import Clock, IdFactory
from budgetlens.domain.money import MoneyAmount
from budgetlens.domain.permissions import require_permission
from budgetlens.domain.variance import compute_variance, favorability_for_account_types
from budgetlens.ports.storage import ObjectStorage


@dataclass(frozen=True, slots=True)
class AnalyticsQuery:
    fiscal_year: int
    period_from: date
    period_to: date
    budget_version_id: UUID
    account_ids: tuple[UUID, ...]
    department_ids: tuple[UUID, ...]
    cost_center_ids: tuple[UUID, ...]

    def __post_init__(self) -> None:
        if self.period_from.day != 1 or self.period_to.day != 1:
            raise ValidationError(
                "INVALID_PERIOD",
                "El periodo debe usar el primer día de cada mes.",
                field_errors=[field_issue("period_from", "INVALID_PERIOD", "Usa YYYY-MM-01.")],
            )
        if self.period_to < self.period_from:
            raise ValidationError(
                "INVALID_PERIOD",
                "El periodo final no puede ser anterior al inicial.",
            )


@dataclass(frozen=True, slots=True)
class VarianceMetrics:
    budget_amount: MoneyAmount
    actual_amount: MoneyAmount
    variance_amount: MoneyAmount
    variance_percent: str | None
    variance_state: str
    favorability: str

    def as_dict(self) -> dict[str, str | None]:
        return {
            "budget_amount": self.budget_amount.as_text(),
            "actual_amount": self.actual_amount.as_text(),
            "variance_amount": self.variance_amount.as_text(),
            "variance_percent": self.variance_percent,
            "variance_state": self.variance_state,
            "favorability": self.favorability,
        }


@dataclass(frozen=True, slots=True)
class BreakdownItem:
    group_id: str
    group_code: str
    group_name: str
    metrics: VarianceMetrics


@dataclass(frozen=True, slots=True)
class VarianceSummary:
    query: AnalyticsQuery
    currency: str
    metrics: VarianceMetrics


def parse_analytics_query(
    *,
    fiscal_year: int,
    period_from: date,
    period_to: date,
    budget_version_id: UUID,
    account_ids: list[UUID] | None = None,
    department_ids: list[UUID] | None = None,
    cost_center_ids: list[UUID] | None = None,
) -> AnalyticsQuery:
    return AnalyticsQuery(
        fiscal_year=fiscal_year,
        period_from=period_from,
        period_to=period_to,
        budget_version_id=budget_version_id,
        account_ids=tuple(account_ids or ()),
        department_ids=tuple(department_ids or ()),
        cost_center_ids=tuple(cost_center_ids or ()),
    )


class AnalyticsService:
    def __init__(
        self,
        session: Session,
        clock: Clock,
        ids: IdFactory,
        storage: ObjectStorage,
    ) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids
        self._storage = storage
        self._orgs = SqlOrganizationRepository(session)
        self._audits = SqlAuditRepository(session)

    def summary(self, context: TenantContext, query: AnalyticsQuery) -> VarianceSummary:
        self._assert_version(context, query.budget_version_id)
        organization = self._orgs.get(context.organization_id)
        if organization is None:
            raise NotFoundError()
        budget, actual, types = self._aggregate(context.organization_id, query, group_expr=None)
        metrics = build_variance_metrics(budget, actual, types)
        return VarianceSummary(
            query=query, currency=organization.functional_currency.code, metrics=metrics
        )

    def breakdown(
        self,
        context: TenantContext,
        query: AnalyticsQuery,
        *,
        group_by: AnalyticsGroupBy,
        sort: AnalyticsSort,
        direction: SortDirection,
        cursor: str | None,
        limit: int | None,
    ) -> Page[BreakdownItem]:
        self._assert_version(context, query.budget_version_id)
        items = self._breakdown_items(context.organization_id, query, group_by)
        items = _sort_items(items, sort, direction)
        page_limit = clamp_limit(limit)
        offset = 0
        parsed = decode_cursor(cursor)
        if parsed is not None:
            offset = int(parsed["offset"])
        window = items[offset : offset + page_limit + 1]
        has_more = len(window) > page_limit
        page_items = window[:page_limit]
        next_cursor = encode_cursor({"offset": str(offset + page_limit)}) if has_more else None
        return Page(items=page_items, next_cursor=next_cursor, has_more=has_more)

    def top_unfavorable(
        self,
        context: TenantContext,
        query: AnalyticsQuery,
        *,
        group_by: AnalyticsGroupBy,
        limit: int,
    ) -> list[BreakdownItem]:
        self._assert_version(context, query.budget_version_id)
        capped = min(max(limit, 1), 20)
        items = [
            item
            for item in self._breakdown_items(context.organization_id, query, group_by)
            if item.metrics.favorability == "unfavorable"
        ]
        items = _sort_items(items, AnalyticsSort.ABSOLUTE_VARIANCE, SortDirection.DESC)
        return items[:capped]

    def compare_periods(
        self,
        context: TenantContext,
        query: AnalyticsQuery,
        *,
        compare_from: date,
        compare_to: date,
    ) -> dict[str, VarianceSummary]:
        left = AnalyticsQuery(
            fiscal_year=query.fiscal_year,
            period_from=query.period_from,
            period_to=query.period_to,
            budget_version_id=query.budget_version_id,
            account_ids=query.account_ids,
            department_ids=query.department_ids,
            cost_center_ids=query.cost_center_ids,
        )
        right = AnalyticsQuery(
            fiscal_year=query.fiscal_year,
            period_from=compare_from,
            period_to=compare_to,
            budget_version_id=query.budget_version_id,
            account_ids=query.account_ids,
            department_ids=query.department_ids,
            cost_center_ids=query.cost_center_ids,
        )
        return {"baseline": self.summary(context, left), "comparison": self.summary(context, right)}

    def export_breakdown(
        self,
        context: TenantContext,
        query: AnalyticsQuery,
        *,
        group_by: AnalyticsGroupBy,
    ) -> ExportJob:
        require_permission(context.role, Permission.EXPORT)
        enforce_limit(
            "export",
            context.user.id,
            limit=get_settings().rate_limit_export_per_minute,
        )
        summary = self.summary(context, query)
        items = self._breakdown_items(context.organization_id, query, group_by)
        items = _sort_items(items, AnalyticsSort.ABSOLUTE_VARIANCE, SortDirection.DESC)
        headers = (
            "organization_id",
            "currency",
            "budget_version_id",
            "period_from",
            "period_to",
            "generated_at",
            "group_code",
            "group_name",
            "budget_amount",
            "actual_amount",
            "variance_amount",
            "variance_percent",
            "favorability",
            "variance_state",
        )
        generated = self._clock.now().isoformat()
        rows = [
            [
                str(context.organization_id),
                summary.currency,
                str(query.budget_version_id),
                query.period_from.isoformat(),
                query.period_to.isoformat(),
                generated,
                item.group_code,
                item.group_name,
                item.metrics.budget_amount.as_text(),
                item.metrics.actual_amount.as_text(),
                item.metrics.variance_amount.as_text(),
                item.metrics.variance_percent or "",
                item.metrics.favorability,
                item.metrics.variance_state,
            ]
            for item in items
        ]
        content = render_csv(headers, rows)
        filename = export_filename(period_from=query.period_from, period_to=query.period_to)
        key = self._storage.generate_key(
            organization_id=context.organization_id,
            namespace=f"exports/{self._ids.new_id()}",
            name=filename,
        )
        self._storage.put(key, content, content_type="text/csv")
        job = ExportJob(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            created_by=context.user.id,
            export_type=ExportType.VARIANCE_BREAKDOWN,
            format="csv",
            filters_json={
                "fiscal_year": query.fiscal_year,
                "period_from": query.period_from.isoformat(),
                "period_to": query.period_to.isoformat(),
                "budget_version_id": str(query.budget_version_id),
                "group_by": group_by.value,
            },
            object_key=key,
            filename=filename,
            status=ExportJobStatus.READY,
            created_at=self._clock.now(),
            expires_at=self._clock.now() + timedelta(hours=24),
        )
        SqlExportJobRepository(self._session, context.organization_id).add(job)
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action="export.create",
            resource_type="export_job",
            resource_id=job.id,
            trace_id=context.trace_id,
            metadata={"export_type": job.export_type.value},
        )
        return job

    def get_export(self, context: TenantContext, export_id: UUID) -> tuple[ExportJob, bytes]:
        require_permission(context.role, Permission.EXPORT)
        job = SqlExportJobRepository(self._session, context.organization_id).get(export_id)
        if job is None:
            raise NotFoundError()
        job.assert_downloadable(now=self._clock.now())
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action="export.download_authorized",
            resource_type="export_job",
            resource_id=job.id,
            trace_id=context.trace_id,
            metadata={"export_type": job.export_type.value},
        )
        return job, self._storage.get(job.object_key)

    def _assert_version(self, context: TenantContext, version_id: UUID) -> None:
        version = SqlBudgetVersionRepository(self._session, context.organization_id).get(version_id)
        if version is None:
            raise NotFoundError()

    def _breakdown_items(
        self, organization_id: UUID, query: AnalyticsQuery, group_by: AnalyticsGroupBy
    ) -> list[BreakdownItem]:
        group_id, group_code, group_name = _group_columns(group_by)
        rows = self._session.execute(
            self._base_select(organization_id, query, group_id, group_code, group_name)
        ).all()
        items: list[BreakdownItem] = []
        for row in rows:
            types = _parse_types(row.account_types)
            items.append(
                BreakdownItem(
                    group_id=str(row.group_id),
                    group_code=str(row.group_code),
                    group_name=str(row.group_name),
                    metrics=build_variance_metrics(
                        MoneyAmount(row.budget_amount), MoneyAmount(row.actual_amount), types
                    ),
                )
            )
        return items

    def _aggregate(
        self,
        organization_id: UUID,
        query: AnalyticsQuery,
        group_expr: Any,
    ) -> tuple[MoneyAmount, MoneyAmount, list[AccountType]]:
        del group_expr
        stmt = select(
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                FinancialEntryRow.scenario_type == "budget",
                                FinancialEntryRow.budget_version_id == query.budget_version_id,
                            ),
                            FinancialEntryRow.amount,
                        ),
                        else_=literal(0),
                    )
                ),
                0,
            ).label("budget_amount"),
            func.coalesce(
                func.sum(
                    case(
                        (FinancialEntryRow.scenario_type == "actual", FinancialEntryRow.amount),
                        else_=literal(0),
                    )
                ),
                0,
            ).label("actual_amount"),
            func.min(AccountRow.account_type).label("min_type"),
            func.max(AccountRow.account_type).label("max_type"),
        )
        stmt = self._apply_filters(stmt, organization_id, query).join(
            AccountRow,
            and_(
                AccountRow.id == FinancialEntryRow.account_id,
                AccountRow.organization_id == FinancialEntryRow.organization_id,
            ),
        )
        row = self._session.execute(stmt).one()
        types: list[AccountType] = []
        if row.min_type:
            types.append(AccountType(row.min_type))
            if row.max_type and row.max_type != row.min_type:
                types.append(AccountType(row.max_type))
        return MoneyAmount(row.budget_amount or 0), MoneyAmount(row.actual_amount or 0), types

    def _base_select(
        self,
        organization_id: UUID,
        query: AnalyticsQuery,
        group_id: Any,
        group_code: Any,
        group_name: Any,
    ) -> Select[Any]:
        stmt = select(
            group_id.label("group_id"),
            group_code.label("group_code"),
            group_name.label("group_name"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                FinancialEntryRow.scenario_type == "budget",
                                FinancialEntryRow.budget_version_id == query.budget_version_id,
                            ),
                            FinancialEntryRow.amount,
                        ),
                        else_=literal(0),
                    )
                ),
                0,
            ).label("budget_amount"),
            func.coalesce(
                func.sum(
                    case(
                        (FinancialEntryRow.scenario_type == "actual", FinancialEntryRow.amount),
                        else_=literal(0),
                    )
                ),
                0,
            ).label("actual_amount"),
            func.min(AccountRow.account_type).label("min_type"),
            func.max(AccountRow.account_type).label("max_type"),
            (
                func.min(AccountRow.account_type) + literal(",") + func.max(AccountRow.account_type)
            ).label("account_types"),
        )
        stmt = self._apply_filters(stmt, organization_id, query)
        stmt = stmt.join(
            AccountRow,
            and_(
                AccountRow.id == FinancialEntryRow.account_id,
                AccountRow.organization_id == FinancialEntryRow.organization_id,
            ),
        )
        if group_id is DepartmentRow.id:
            stmt = stmt.join(
                DepartmentRow,
                and_(
                    DepartmentRow.id == FinancialEntryRow.department_id,
                    DepartmentRow.organization_id == FinancialEntryRow.organization_id,
                ),
            )
        if group_id is CostCenterRow.id:
            stmt = stmt.join(
                CostCenterRow,
                and_(
                    CostCenterRow.id == FinancialEntryRow.cost_center_id,
                    CostCenterRow.organization_id == FinancialEntryRow.organization_id,
                ),
            )
        return stmt.group_by(group_id, group_code, group_name)

    def _apply_filters(
        self, stmt: Select[Any], organization_id: UUID, query: AnalyticsQuery
    ) -> Select[Any]:
        stmt = stmt.where(
            FinancialEntryRow.organization_id == organization_id,
            FinancialEntryRow.fiscal_year == query.fiscal_year,
            FinancialEntryRow.period_start >= query.period_from,
            FinancialEntryRow.period_start <= query.period_to,
            or_(
                and_(
                    FinancialEntryRow.scenario_type == "budget",
                    FinancialEntryRow.budget_version_id == query.budget_version_id,
                ),
                FinancialEntryRow.scenario_type == "actual",
            ),
        )
        if query.account_ids:
            stmt = stmt.where(FinancialEntryRow.account_id.in_(query.account_ids))
        if query.department_ids:
            stmt = stmt.where(FinancialEntryRow.department_id.in_(query.department_ids))
        if query.cost_center_ids:
            stmt = stmt.where(FinancialEntryRow.cost_center_id.in_(query.cost_center_ids))
        return stmt


def _group_columns(group_by: AnalyticsGroupBy) -> tuple[Any, Any, Any]:
    if group_by is AnalyticsGroupBy.PERIOD:
        return (
            FinancialEntryRow.period_start,
            FinancialEntryRow.period_start,
            FinancialEntryRow.period_start,
        )
    if group_by is AnalyticsGroupBy.ACCOUNT:
        return AccountRow.id, AccountRow.code, AccountRow.name
    if group_by is AnalyticsGroupBy.DEPARTMENT:
        return DepartmentRow.id, DepartmentRow.code, DepartmentRow.name
    return CostCenterRow.id, CostCenterRow.code, CostCenterRow.name


def build_variance_metrics(
    budget: MoneyAmount, actual: MoneyAmount, types: list[AccountType]
) -> VarianceMetrics:
    account_type = types[0] if len(types) == 1 else None
    computed = compute_variance(
        actual_amount=actual, budget_amount=budget, account_type=account_type
    )
    favorability = favorability_for_account_types(computed.variance_amount, types)
    return VarianceMetrics(
        budget_amount=computed.budget_amount,
        actual_amount=computed.actual_amount,
        variance_amount=computed.variance_amount,
        variance_percent=computed.percent_as_text(),
        variance_state=computed.variance_state.value,
        favorability=favorability.value,
    )


def _sort_items(
    items: list[BreakdownItem], sort: AnalyticsSort, direction: SortDirection
) -> list[BreakdownItem]:
    def key(item: BreakdownItem) -> tuple[object, ...]:
        metrics = item.metrics
        if sort is AnalyticsSort.BUDGET_AMOUNT:
            primary = metrics.budget_amount.value
        elif sort is AnalyticsSort.ACTUAL_AMOUNT:
            primary = metrics.actual_amount.value
        elif sort is AnalyticsSort.ABSOLUTE_VARIANCE:
            primary = abs(metrics.variance_amount.value)
        else:
            primary = metrics.variance_amount.value
        return (primary, item.group_code, item.group_id)

    reverse = direction is SortDirection.DESC
    return sorted(items, key=key, reverse=reverse)


def _parse_types(value: object) -> list[AccountType]:
    if not value:
        return []
    parts = {item for item in str(value).split(",") if item}
    return [AccountType(item) for item in parts]
