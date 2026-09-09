import type { AnalysisFilters, GroupByDimension } from "./analysis-filters";
import { copy } from "./copy";
import { groupByLabel, sortOptionLabel } from "./labels";

export const DASHBOARD_EXPORT_GROUP: GroupByDimension = "department";

export function exportScopeText(
  currency: string,
  periodLabel: string,
  groupBy: GroupByDimension,
  sort: AnalysisFilters["sort"],
): string {
  return [
    currency,
    periodLabel,
    `${copy.groupByLabel}: ${groupByLabel(groupBy)}`,
    `${copy.filterSort}: ${sortOptionLabel(sort)}`,
  ]
    .filter(Boolean)
    .join(" · ");
}
