import { describe, expect, it } from "vitest";
import type { BudgetVersion } from "@budgetlens/api-client";

import { EMPTY_ANALYSIS_FILTERS } from "@/lib/analysis-filters";
import { queryFromFilters } from "@/lib/query-from-filters";

describe("queryFromFilters", () => {
  const version = {
    id: "v1",
    fiscal_year: 2026,
    is_active: true,
    status: "published",
  } as BudgetVersion;

  it("returns null until a budget version is selected", () => {
    expect(queryFromFilters(EMPTY_ANALYSIS_FILTERS, [version], 1)).toBeNull();
  });

  it("fills the fiscal year when periods are omitted", () => {
    const query = queryFromFilters(
      { ...EMPTY_ANALYSIS_FILTERS, budgetVersionId: "v1" },
      [version],
      1,
    );
    expect(query).toMatchObject({
      fiscal_year: 2026,
      period_from: "2026-01-01",
      period_to: "2026-12-01",
      budget_version_id: "v1",
    });
  });
});
