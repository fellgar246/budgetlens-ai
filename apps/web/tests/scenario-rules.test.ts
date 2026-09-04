import { describe, expect, it } from "vitest";

import { draftsFromSavedRules, ratioToPercent, stripMoneyScale } from "@/lib/scenario-rules";

describe("scenario rule drafts", () => {
  it("converts stored ratios back to percents without float math", () => {
    expect(ratioToPercent("0.050000")).toBe("5");
    expect(ratioToPercent("0.125000")).toBe("12.5");
    expect(stripMoneyScale("10.0000")).toBe("10");
  });

  it("reloads saved rules in sequence", () => {
    const drafts = draftsFromSavedRules(
      [
        {
          sequence: 1,
          operation: "percentage_change",
          value: "0.0500",
          scope: {
            period_from: "2027-01-01",
            period_to: "2027-03-01",
            department_ids: ["dept-ops"],
          },
        },
      ],
      "2027-01-01",
      "2027-12-01",
    );
    expect(drafts).toEqual([
      {
        operation: "percentage_change",
        value: "5",
        departmentId: "dept-ops",
        periodFrom: "2027-01-01",
        periodTo: "2027-03-01",
      },
    ]);
  });
});
