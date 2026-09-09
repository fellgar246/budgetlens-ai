import { describe, expect, it } from "vitest";

import {
  asEvidenceRecords,
  itemSummaries,
  metricPairs,
  scopeLines,
} from "@/features/copilot/evidence";

describe("copilot evidence helpers", () => {
  it("keeps a closed set of aggregates and does not invent extra rows", () => {
    const records = asEvidenceRecords([
      {
        id: "ev_1",
        tool: "get_variance_summary",
        label: "Resumen de variación",
        data: {
          currency: "MXN",
          metrics: {
            budget_amount: "100000.0000",
            actual_amount: "130000.0000",
            variance_amount: "30000.0000",
            extra_secret: "should-be-ignored-as-row-dump",
          },
        },
      },
    ]);
    expect(records).toHaveLength(1);
    expect(metricPairs(records[0].data)).toEqual([
      { label: "Presupuesto", value: "100000.0000", money: true },
      { label: "Real", value: "130000.0000", money: true },
      { label: "Variación", value: "30000.0000", money: true },
    ]);
    expect(
      scopeLines({ fiscal_year: 2026, period_from: "2026-01-01", period_to: "2026-01-01" }),
    ).toEqual(["Año fiscal: 2026", "Periodo: 2026-01-01 – 2026-01-01"]);
  });

  it("limits breakdown rows shown as evidence", () => {
    const items = Array.from({ length: 12 }, (_, index) => ({
      group_name: `Cuenta ${index}`,
      variance_amount: `${index}.0000`,
    }));
    expect(itemSummaries({ items })).toHaveLength(5);
  });
});
