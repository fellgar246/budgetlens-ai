from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from budgetlens.domain.enums import ScenarioType
from budgetlens.domain.errors import ValidationError
from budgetlens.domain.money import Currency, MoneyAmount
from budgetlens.domain.organization import Organization, require_same_organization


@dataclass(frozen=True, slots=True)
class FinancialEntry:
    id: UUID
    organization_id: UUID
    import_job_id: UUID
    scenario_type: ScenarioType
    budget_version_id: UUID | None
    period_start: date
    fiscal_year: int
    account_id: UUID
    department_id: UUID
    cost_center_id: UUID
    amount: MoneyAmount
    currency: Currency
    source_row_number: int
    source_reference: str | None
    created_at: datetime

    def __post_init__(self) -> None:
        if self.period_start.day != 1:
            raise ValidationError(
                "INVALID_PERIOD", "El periodo debe iniciar el primer día del mes."
            )
        if self.scenario_type is ScenarioType.BUDGET and self.budget_version_id is None:
            raise ValidationError(
                "BUDGET_VERSION_REQUIRED",
                "Las filas de presupuesto requieren una versión.",
            )
        if self.scenario_type is ScenarioType.ACTUAL and self.budget_version_id is not None:
            raise ValidationError(
                "BUDGET_VERSION_FORBIDDEN",
                "Las filas reales no aceptan versión de presupuesto.",
            )

    def assert_consistent_with(self, organization: Organization) -> None:
        require_same_organization(organization.id, self.organization_id)
        if not self.currency.matches(organization.functional_currency):
            raise ValidationError(
                "CURRENCY_MISMATCH",
                "La moneda de la fila no coincide con la moneda funcional.",
            )
        expected_year = organization.period_for(self.period_start).fiscal_year
        if self.fiscal_year != expected_year:
            raise ValidationError(
                "INVALID_FISCAL_YEAR",
                "El año fiscal no coincide con el periodo.",
            )
