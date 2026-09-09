from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.finance_repositories import (
    SqlAnalyticsRepository,
    SqlExportJobRepository,
)
from budgetlens.adapters.persistence.repositories import (
    SqlAuditRepository,
    SqlBudgetVersionRepository,
    SqlOrganizationRepository,
)
from budgetlens.application.analytics_query import (
    AnalyticsQuery,
    BreakdownItem,
    VarianceMetrics,
    VarianceSummary,
    build_variance_metrics,
    parse_analytics_query,
    sort_breakdown_items,
)
from budgetlens.application.audit import record_audit
from budgetlens.application.context import TenantContext
from budgetlens.application.pagination import Page, offset_page
from budgetlens.application.rate_limit import enforce_limit
from budgetlens.config import get_settings
from budgetlens.domain.audit import EXPORT_CREATED, EXPORT_DOWNLOAD_AUTHORIZED
from budgetlens.domain.enums import (
    AnalyticsGroupBy,
    AnalyticsSort,
    ExportJobStatus,
    ExportType,
    Permission,
    SortDirection,
)
from budgetlens.domain.errors import NotFoundError
from budgetlens.domain.exporting import ExportJob, export_filename, render_csv
from budgetlens.domain.identities import Clock, IdFactory
from budgetlens.domain.permissions import require_permission
from budgetlens.ports.exports import ExportExecutor
from budgetlens.ports.storage import ObjectStorage

__all__ = [
    "AnalyticsQuery",
    "AnalyticsService",
    "BreakdownItem",
    "VarianceMetrics",
    "VarianceSummary",
    "build_variance_metrics",
    "parse_analytics_query",
]


class AnalyticsService:
    def __init__(
        self,
        session: Session,
        clock: Clock,
        ids: IdFactory,
        storage: ObjectStorage,
        executor: ExportExecutor,
    ) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids
        self._storage = storage
        self._executor = executor
        self._orgs = SqlOrganizationRepository(session)
        self._audits = SqlAuditRepository(session)

    def _repo(self, organization_id: UUID) -> SqlAnalyticsRepository:
        return SqlAnalyticsRepository(self._session, organization_id)

    def summary(self, context: TenantContext, query: AnalyticsQuery) -> VarianceSummary:
        self._assert_version(context, query.budget_version_id)
        organization = self._orgs.get(context.organization_id)
        if organization is None:
            raise NotFoundError()
        totals = self._repo(context.organization_id).totals(query)
        metrics = build_variance_metrics(
            totals.budget_amount, totals.actual_amount, totals.account_types
        )
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
        items = sort_breakdown_items(
            self._breakdown_items(context.organization_id, query, group_by), sort, direction
        )
        return offset_page(items, cursor=cursor, limit=limit)

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
        items = sort_breakdown_items(items, AnalyticsSort.ABSOLUTE_VARIANCE, SortDirection.DESC)
        return items[:capped]

    def compare_periods(
        self,
        context: TenantContext,
        query: AnalyticsQuery,
        *,
        compare_from: date,
        compare_to: date,
    ) -> dict[str, VarianceSummary]:
        right = parse_analytics_query(
            fiscal_year=query.fiscal_year,
            period_from=compare_from,
            period_to=compare_to,
            budget_version_id=query.budget_version_id,
            account_ids=list(query.account_ids),
            department_ids=list(query.department_ids),
            cost_center_ids=list(query.cost_center_ids),
        )
        return {
            "baseline": self.summary(context, query),
            "comparison": self.summary(context, right),
        }

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
            organization_id=context.organization_id,
            limit=get_settings().rate_limit_export_per_minute,
        )
        return self._executor.run(
            "export",
            lambda: self._render_export(context, query, group_by=group_by),
        )

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
            action=EXPORT_DOWNLOAD_AUTHORIZED,
            resource_type="export_job",
            resource_id=job.id,
            trace_id=context.trace_id,
            metadata={"export_type": job.export_type.value},
        )
        return job, self._storage.get(job.object_key)

    def _render_export(
        self,
        context: TenantContext,
        query: AnalyticsQuery,
        *,
        group_by: AnalyticsGroupBy,
    ) -> ExportJob:
        summary = self.summary(context, query)
        items = sort_breakdown_items(
            self._breakdown_items(context.organization_id, query, group_by),
            AnalyticsSort.ABSOLUTE_VARIANCE,
            SortDirection.DESC,
        )
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
        settings = get_settings()
        content = render_csv(headers, rows, with_bom=settings.csv_export_with_bom)
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
            expires_at=self._clock.now() + timedelta(hours=settings.export_retention_hours),
        )
        SqlExportJobRepository(self._session, context.organization_id).add(job)
        record_audit(
            self._audits,
            clock=self._clock,
            ids=self._ids,
            organization_id=context.organization_id,
            actor_id=context.user.id,
            action=EXPORT_CREATED,
            resource_type="export_job",
            resource_id=job.id,
            trace_id=context.trace_id,
            metadata={"export_type": job.export_type.value},
        )
        return job

    def _assert_version(self, context: TenantContext, version_id: UUID) -> None:
        version = SqlBudgetVersionRepository(self._session, context.organization_id).get(version_id)
        if version is None:
            raise NotFoundError()

    def _breakdown_items(
        self, organization_id: UUID, query: AnalyticsQuery, group_by: AnalyticsGroupBy
    ) -> list[BreakdownItem]:
        return [
            BreakdownItem(
                group_id=row.group_id,
                group_code=row.group_code,
                group_name=row.group_name,
                metrics=build_variance_metrics(
                    row.budget_amount, row.actual_amount, row.account_types
                ),
            )
            for row in self._repo(organization_id).grouped_totals(query, group_by)
        ]
