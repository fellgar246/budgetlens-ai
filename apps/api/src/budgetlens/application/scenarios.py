from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from budgetlens.adapters.persistence.finance_repositories import SqlScenarioRepository
from budgetlens.adapters.persistence.models import FinancialEntryRow
from budgetlens.adapters.persistence.repositories import (
    SqlAuditRepository,
    SqlBudgetVersionRepository,
)
from budgetlens.application.analytics import AnalyticsQuery, build_variance_metrics
from budgetlens.application.context import TenantContext
from budgetlens.application.pagination import Page, clamp_limit
from budgetlens.domain.enums import (
    AccountType,
    Permission,
    ScenarioOperation,
    ScenarioStatus,
    ScenarioType,
)
from budgetlens.domain.errors import NotFoundError, ValidationError
from budgetlens.domain.identities import Clock, IdFactory
from budgetlens.domain.money import MoneyAmount
from budgetlens.domain.organization import normalize_name
from budgetlens.domain.permissions import require_permission
from budgetlens.domain.scenario import (
    Scenario,
    ScenarioRule,
    ScenarioScope,
    apply_scenario_rules,
    rule_applies,
)


class ScenarioService:
    def __init__(self, session: Session, clock: Clock, ids: IdFactory) -> None:
        self._session = session
        self._clock = clock
        self._ids = ids
        self._audits = SqlAuditRepository(session)

    def _repo(self, organization_id: UUID) -> SqlScenarioRepository:
        return SqlScenarioRepository(self._session, organization_id, self._ids)

    def list(
        self, context: TenantContext, *, cursor: str | None, limit: int | None
    ) -> Page[Scenario]:
        return self._repo(context.organization_id).list_page(
            cursor=cursor, limit=clamp_limit(limit)
        )

    def get(self, context: TenantContext, scenario_id: UUID) -> Scenario:
        scenario = self._repo(context.organization_id).get(scenario_id)
        if scenario is None:
            raise NotFoundError()
        return scenario

    def create(
        self,
        context: TenantContext,
        *,
        name: str,
        baseline_type: ScenarioType,
        budget_version_id: UUID | None,
        fiscal_year: int,
        rules: list[ScenarioRule],
    ) -> Scenario:
        require_permission(context.role, Permission.CREATE_SCENARIOS)
        if baseline_type is ScenarioType.BUDGET:
            if budget_version_id is None:
                raise ValidationError(
                    "BUDGET_VERSION_REQUIRED", "El escenario de presupuesto requiere una versión."
                )
            version = SqlBudgetVersionRepository(self._session, context.organization_id).get(
                budget_version_id
            )
            if version is None:
                raise NotFoundError()
        now = self._clock.now()
        scenario = Scenario(
            id=self._ids.new_id(),
            organization_id=context.organization_id,
            created_by=context.user.id,
            name=normalize_name(name, field="name", max_length=160),
            baseline_type=baseline_type,
            budget_version_id=budget_version_id,
            fiscal_year=fiscal_year,
            status=ScenarioStatus.SAVED,
            created_at=now,
            updated_at=now,
            rules=tuple(rules),
        )
        self._repo(context.organization_id).add(scenario)
        return scenario

    def update(
        self,
        context: TenantContext,
        *,
        scenario_id: UUID,
        name: str | None,
        rules: list[ScenarioRule] | None,
    ) -> Scenario:
        require_permission(context.role, Permission.CREATE_SCENARIOS)
        current = self.get(context, scenario_id)
        updated = current.with_draft_update(now=self._clock.now(), name=name, rules=rules)
        self._repo(context.organization_id).save(updated)
        return updated

    def archive(self, context: TenantContext, *, scenario_id: UUID) -> Scenario:
        require_permission(context.role, Permission.CREATE_SCENARIOS)
        updated = self.get(context, scenario_id).archive(now=self._clock.now())
        self._repo(context.organization_id).save(updated)
        return updated

    def preview(
        self,
        context: TenantContext,
        *,
        query: AnalyticsQuery,
        baseline_type: ScenarioType,
        rules: list[ScenarioRule],
    ) -> dict[str, object]:
        grains = self._baseline_grains(context.organization_id, query, baseline_type)
        baseline_total = MoneyAmount("0")
        result_total = MoneyAmount("0")
        monthly: dict[date, tuple[MoneyAmount, MoneyAmount]] = {}
        for grain in grains:
            outcome = apply_scenario_rules(
                grain.amount, _matching_rules(rules, grain), created_at=self._clock.now()
            )
            baseline_total = baseline_total + grain.amount
            result_total = result_total + outcome.result
            current = monthly.get(grain.period_start, (MoneyAmount("0"), MoneyAmount("0")))
            monthly[grain.period_start] = (current[0] + grain.amount, current[1] + outcome.result)
        types = [AccountType.EXPENSE] if not grains else grains[0].account_types
        comparison = build_variance_metrics(baseline_total, result_total, types)
        return {
            "baseline": baseline_total.as_text(),
            "result": result_total.as_text(),
            "metrics": comparison.as_dict(),
            "monthly": [
                {
                    "period": period.isoformat(),
                    "baseline": amounts[0].as_text(),
                    "result": amounts[1].as_text(),
                }
                for period, amounts in sorted(monthly.items())
            ],
        }

    def compare(
        self, context: TenantContext, *, scenario_id: UUID, query: AnalyticsQuery
    ) -> dict[str, object]:
        scenario = self.get(context, scenario_id)
        return self.preview(
            context,
            query=query,
            baseline_type=scenario.baseline_type,
            rules=list(scenario.rules),
        )

    def _baseline_grains(
        self, organization_id: UUID, query: AnalyticsQuery, baseline_type: ScenarioType
    ) -> list[_Grain]:
        stmt = (
            select(
                FinancialEntryRow.period_start,
                FinancialEntryRow.account_id,
                FinancialEntryRow.department_id,
                FinancialEntryRow.cost_center_id,
                func.min(FinancialEntryRow.amount * 0).label("pad"),
                func.coalesce(func.sum(FinancialEntryRow.amount), 0).label("amount"),
            )
            .where(
                FinancialEntryRow.organization_id == organization_id,
                FinancialEntryRow.fiscal_year == query.fiscal_year,
                FinancialEntryRow.period_start >= query.period_from,
                FinancialEntryRow.period_start <= query.period_to,
                FinancialEntryRow.scenario_type == baseline_type.value,
            )
            .group_by(
                FinancialEntryRow.period_start,
                FinancialEntryRow.account_id,
                FinancialEntryRow.department_id,
                FinancialEntryRow.cost_center_id,
            )
        )
        if baseline_type is ScenarioType.BUDGET:
            stmt = stmt.where(FinancialEntryRow.budget_version_id == query.budget_version_id)
        if query.account_ids:
            stmt = stmt.where(FinancialEntryRow.account_id.in_(query.account_ids))
        if query.department_ids:
            stmt = stmt.where(FinancialEntryRow.department_id.in_(query.department_ids))
        if query.cost_center_ids:
            stmt = stmt.where(FinancialEntryRow.cost_center_id.in_(query.cost_center_ids))
        rows = self._session.execute(stmt).all()
        return [
            _Grain(
                period_start=row.period_start,
                account_id=row.account_id,
                department_id=row.department_id,
                cost_center_id=row.cost_center_id,
                amount=MoneyAmount(row.amount),
                account_types=[AccountType.EXPENSE],
            )
            for row in rows
        ]


class _Grain:
    def __init__(
        self,
        *,
        period_start: date,
        account_id: UUID,
        department_id: UUID,
        cost_center_id: UUID,
        amount: MoneyAmount,
        account_types: list[AccountType],
    ) -> None:
        self.period_start = period_start
        self.account_id = account_id
        self.department_id = department_id
        self.cost_center_id = cost_center_id
        self.amount = amount
        self.account_types = account_types


def _matching_rules(rules: list[ScenarioRule], grain: _Grain) -> list[ScenarioRule]:
    return [
        rule
        for rule in rules
        if rule_applies(
            rule,
            period=grain.period_start,
            account_id=grain.account_id,
            department_id=grain.department_id,
            cost_center_id=grain.cost_center_id,
        )
    ]


def parse_rule_payload(payload: dict[str, object]) -> ScenarioRule:
    scope = as_object_map(payload.get("scope"), code="INVALID_SCOPE")
    operation = ScenarioOperation(str(payload.get("operation")))
    value = Decimal(str(payload.get("value")))
    return ScenarioRule(
        sequence=int(str(payload.get("sequence", 1))),
        operation=operation,
        value=value,
        scope=ScenarioScope(
            period_from=date.fromisoformat(str(scope["period_from"])),
            period_to=date.fromisoformat(str(scope["period_to"])),
            account_ids=_uuid_tuple(scope.get("account_ids")),
            department_ids=_uuid_tuple(scope.get("department_ids")),
            cost_center_ids=_uuid_tuple(scope.get("cost_center_ids")),
        ),
    )


def as_object_map(value: object, *, code: str = "INVALID_SCOPE") -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValidationError(code, "El alcance del escenario no es válido.")
    typed = cast(dict[object, object], value)
    return {str(key): item for key, item in typed.items()}


def _uuid_tuple(value: object) -> tuple[UUID, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(UUID(str(item)) for item in cast(list[object], value))
