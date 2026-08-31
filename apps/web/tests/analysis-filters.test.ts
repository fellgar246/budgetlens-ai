import { describe, expect, it } from "vitest";

import {
  EMPTY_ANALYSIS_FILTERS,
  parseAnalysisFilters,
  serializeAnalysisFilters,
  withPathFilters,
} from "@/lib/analysis-filters";

describe("analysis filters", () => {
  it("round-trips URL filters and defaults to unfavorable sort", () => {
    const filters = parseAnalysisFilters(
      "version=abc&period_from=2026-01-01&period_to=2026-06-01&department=d1&sort=unfavorable",
    );
    expect(filters.budgetVersionId).toBe("abc");
    expect(filters.departmentId).toBe("d1");
    expect(filters.sort).toBe("unfavorable");
    expect(serializeAnalysisFilters(filters)).toBe(
      "version=abc&period_from=2026-01-01&period_to=2026-06-01&department=d1",
    );
  });

  it("keeps drill-down filters when building a breadcrumb path", () => {
    const href = withPathFilters("/variances", {
      ...EMPTY_ANALYSIS_FILTERS,
      departmentId: "ops",
      accountId: "6100",
    });
    expect(href).toBe("/variances?department=ops&account=6100");
  });
});
