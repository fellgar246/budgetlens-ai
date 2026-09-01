import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Variance } from "@/components/ui/Variance";
import {
  EMPTY_ANALYSIS_FILTERS,
  parseAnalysisFilters,
  withPathFilters,
} from "@/lib/analysis-filters";
import { copy } from "@/lib/copy";
import { formatPercent } from "@/lib/format";

describe("acceptance display", () => {
  it("shows N/A when percent is missing or budget is zero", () => {
    expect(formatPercent(null)).toBe("N/A");
    render(
      <Variance
        amount="25.0000"
        percent={null}
        favorability="unfavorable"
        currency="MXN"
        budgetAmount="0.0000"
      />,
    );
    expect(screen.getByText(copy.zeroBudgetPercent)).toBeInTheDocument();
  });

  it("keeps drill-down filters on the breadcrumb path", () => {
    const filters = parseAnalysisFilters(
      "version=v1&period_from=2026-01-01&period_to=2026-01-01&department=ops",
    );
    expect(filters.departmentId).toBe("ops");
    expect(withPathFilters("/variances", { ...EMPTY_ANALYSIS_FILTERS, ...filters })).toContain(
      "department=ops",
    );
  });
});
