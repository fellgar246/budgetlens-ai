import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Money } from "@/components/ui/Money";
import { Variance } from "@/components/ui/Variance";
import { copy } from "@/lib/copy";
import { filterDimensionNames, trackEvent, readTelemetry } from "@/lib/analytics";
import { formatMoneyCompact, isZeroAmount } from "@/lib/format";
import { parseAnalysisFilters, serializeAnalysisFilters } from "@/lib/analysis-filters";

describe("UI spec helpers", () => {
  it("formats compact money without losing the exact value", () => {
    expect(formatMoneyCompact("1250000.0000", "MXN")).toContain("M");
    expect(formatMoneyCompact("12500.0000", "MXN")).toContain("k");
    expect(isZeroAmount("0.0000")).toBe(true);
  });

  it("shows N/A with a tooltip when budget is zero", () => {
    render(
      <Variance
        amount="-10.0000"
        percent={null}
        favorability="unfavorable"
        currency="MXN"
        budgetAmount="0.0000"
      />,
    );
    expect(screen.getByText(copy.zeroBudgetPercent)).toBeInTheDocument();
    expect(screen.getByTitle(copy.zeroBudgetHint)).toBeInTheDocument();
  });

  it("keeps exact money available to assistive tech", () => {
    render(<Money value="1250000.0000" currency="MXN" display="compact" />);
    expect(screen.getByText(/MXN 1,250,000.0000|MXN 1.250.000.0000/)).toBeInTheDocument();
  });

  it("serializes group by and cursor in the query string", () => {
    const filters = parseAnalysisFilters("version=abc&group_by=account&cursor=c1");
    expect(filters.groupBy).toBe("account");
    expect(filters.cursor).toBe("c1");
    expect(serializeAnalysisFilters(filters)).toContain("group_by=account");
  });

  it("emits product events without sensitive values", () => {
    window.sessionStorage.clear();
    trackEvent("dashboard_filtered", {
      dimensions: "department",
      amount: "1000",
      question: "should not persist",
    });
    const events = readTelemetry();
    expect(events[0]?.name).toBe("dashboard_filtered");
    expect(events[0]?.properties).toEqual({ dimensions: "department" });
    expect(filterDimensionNames({ departmentId: "d1" })).toEqual(["department"]);
  });
});
