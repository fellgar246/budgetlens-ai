import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ApiRequestError } from "@budgetlens/api-client";

import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Variance } from "@/components/ui/Variance";
import { VarianceBadge } from "@/components/ui/VarianceBadge";
import { copy } from "@/lib/copy";
import { formatMoney, formatPercent, localeForCurrency } from "@/lib/format";

describe("financial display", () => {
  it("always includes currency in amounts", () => {
    expect(formatMoney("12500.2500", "MXN")).toContain("MXN");
    expect(formatMoney("-10.0000", "USD")).toContain("USD");
    expect(localeForCurrency("USD")).toBe("en-US");
    expect(formatMoney("1234.0000", "USD")).toMatch(/USD 1,234\.0000/);
    expect(formatMoney("9999999999999.1234", "MXN").replace(/[^\d.-]/g, "")).toBe(
      "9999999999999.1234",
    );
  });

  it("shows the zero-budget label when the budget is zero", () => {
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
    expect(screen.getByTitle(copy.zeroBudgetHint)).toBeInTheDocument();
  });

  it("shows N/A when the percent is missing", () => {
    expect(formatPercent(null)).toBe("N/A");
    expect(formatPercent("0.000000")).not.toBe("0%");
  });

  it("describes favorability with icon and text", () => {
    render(<VarianceBadge value="favorable" />);
    expect(screen.getByText(copy.favorable)).toBeInTheDocument();
    expect(screen.getByText("↑")).toBeInTheDocument();
  });

  it("shows a corrective action and trace on request errors", () => {
    render(
      <ErrorBanner error={new ApiRequestError("No se pudo guardar.", 422, "trace-error-1")} />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("No se pudo guardar.");
    expect(screen.getByText(copy.errorCorrective)).toBeInTheDocument();
    expect(screen.getByText("trace-error-1")).toBeInTheDocument();
  });
});
