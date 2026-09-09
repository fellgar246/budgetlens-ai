import { describe, expect, it } from "vitest";

import { copy } from "@/lib/copy";
import { DASHBOARD_EXPORT_GROUP, exportScopeText } from "@/lib/export-scope";
import { groupByLabel, importFieldLabel, memberRoleLabel } from "@/lib/labels";

describe("export scope and labels", () => {
  it("describes the visible dashboard breakdown", () => {
    expect(DASHBOARD_EXPORT_GROUP).toBe("department");
    const scope = exportScopeText("MXN", "2026-01-01 – 2026-12-01", "department", "unfavorable");
    expect(scope).toContain("MXN");
    expect(scope).toContain(copy.groupByDepartment);
    expect(scope).toContain(copy.sortUnfavorable);
    expect(scope).not.toContain(copy.groupByAccount);
  });

  it("keeps variance export labels in Spanish", () => {
    expect(groupByLabel("account")).toBe(copy.groupByAccount);
    expect(importFieldLabel("period")).toBe(copy.periodLabel);
    expect(memberRoleLabel("analyst")).toBe(copy.roleAnalyst);
  });
});
