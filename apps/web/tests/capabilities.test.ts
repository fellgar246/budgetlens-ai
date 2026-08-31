import { describe, expect, it } from "vitest";

import { EMPTY_CAPABILITIES, visibleNavGroups } from "@/lib/capabilities";

describe("capability navigation", () => {
  it("hides financial journeys from the operator", () => {
    const groups = visibleNavGroups({
      ...EMPTY_CAPABILITIES,
      can_view_technical_metrics: true,
      can_deploy_rollback: true,
    });
    const hrefs = groups.flatMap((group) => group.items.map((item) => item.href));
    expect(hrefs).toEqual(["/estado"]);
  });

  it("shows dashboard and copilot to a budget owner, but not import or members", () => {
    const groups = visibleNavGroups({
      ...EMPTY_CAPABILITIES,
      can_view_dashboard: true,
      can_use_copilot: true,
      can_export: true,
    });
    const hrefs = groups.flatMap((group) => group.items.map((item) => item.href));
    expect(hrefs).toContain("/dashboard");
    expect(hrefs).toContain("/copilot");
    expect(hrefs).not.toContain("/imports");
    expect(hrefs).not.toContain("/settings/members");
    expect(hrefs).not.toContain("/estado");
  });

  it("shows import, scenarios and members to an organization admin", () => {
    const groups = visibleNavGroups({
      ...EMPTY_CAPABILITIES,
      can_view_dashboard: true,
      can_import: true,
      can_create_scenario: true,
      can_use_copilot: true,
      can_manage_members: true,
      can_manage_organization: true,
      can_manage_dimensions: true,
    });
    const hrefs = groups.flatMap((group) => group.items.map((item) => item.href));
    expect(hrefs).toContain("/imports");
    expect(hrefs).toContain("/scenarios");
    expect(hrefs).toContain("/settings/members");
  });
});
