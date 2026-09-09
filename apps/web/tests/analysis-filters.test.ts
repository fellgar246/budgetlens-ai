import { describe, expect, it } from "vitest";

import type { BudgetVersion } from "@budgetlens/api-client";

import {
  EMPTY_ANALYSIS_FILTERS,
  hasAnalysisFilterParams,
  normalizeAnalysisHref,
  parseAnalysisFilters,
  preferredBudgetVersionId,
  resolveAnalysisFilters,
  serializeAnalysisFilters,
  withDefaultVersion,
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
    expect(href).toBe("/variances/?department=ops&account=6100");
  });

  it("detects an empty query string so stored filters can be restored", () => {
    expect(hasAnalysisFilterParams("")).toBe(false);
    expect(hasAnalysisFilterParams("version=abc")).toBe(true);
  });

  it("prefers the active budget version when the URL has none", () => {
    const versions = [
      { id: "draft", is_active: false, status: "draft" },
      { id: "live", is_active: true, status: "published" },
    ] as BudgetVersion[];
    expect(preferredBudgetVersionId(versions)).toBe("live");
    expect(withDefaultVersion(EMPTY_ANALYSIS_FILTERS, versions).budgetVersionId).toBe("live");
    expect(
      withDefaultVersion({ ...EMPTY_ANALYSIS_FILTERS, budgetVersionId: "draft" }, versions)
        .budgetVersionId,
    ).toBe("draft");
    expect(
      withDefaultVersion({ ...EMPTY_ANALYSIS_FILTERS, budgetVersionId: "other-org" }, versions)
        .budgetVersionId,
    ).toBe("live");
  });

  it("fills the active version when the URL only has group_by", () => {
    const versions = [{ id: "live", is_active: true, status: "published" }] as BudgetVersion[];
    const resolved = resolveAnalysisFilters("group_by=account", null, versions);
    expect(resolved.groupBy).toBe("account");
    expect(resolved.budgetVersionId).toBe("live");
  });

  it("treats trailing slashes as the same analysis href", () => {
    expect(normalizeAnalysisHref("/variances/?version=abc")).toBe(
      normalizeAnalysisHref("/variances?version=abc"),
    );
  });
});
