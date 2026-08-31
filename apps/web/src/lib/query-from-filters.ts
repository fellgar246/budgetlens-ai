import type { AnalyticsQuery, BudgetVersion } from "@budgetlens/api-client";

import type { AnalysisFilters } from "@/lib/analysis-filters";
import { fiscalYearBounds } from "@/lib/format";

export function queryFromFilters(
  filters: AnalysisFilters,
  versions: BudgetVersion[],
  fiscalStartMonth: number,
): AnalyticsQuery | null {
  if (!filters.budgetVersionId) {
    return null;
  }
  const version = versions.find((item) => item.id === filters.budgetVersionId);
  if (!version) {
    return null;
  }
  const bounds = fiscalYearBounds(version.fiscal_year, fiscalStartMonth);
  const periodFrom = filters.periodFrom || bounds.from;
  const periodTo = filters.periodTo || bounds.to;
  if (!periodFrom || !periodTo) {
    return null;
  }
  return {
    fiscal_year: version.fiscal_year,
    period_from: periodFrom,
    period_to: periodTo,
    budget_version_id: version.id,
    account_id: filters.accountId || undefined,
    department_id: filters.departmentId || undefined,
    cost_center_id: filters.costCenterId || undefined,
  };
}
