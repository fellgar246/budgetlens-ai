import type { Capabilities } from "@budgetlens/api-client";

import { copy } from "@/lib/copy";

export const EMPTY_CAPABILITIES: Capabilities = {
  can_view_dashboard: false,
  can_import: false,
  can_publish_budget: false,
  can_create_scenario: false,
  can_use_copilot: false,
  can_manage_members: false,
  can_view_technical_metrics: false,
  can_deploy_rollback: false,
  can_export: false,
  can_manage_versions: false,
  can_manage_dimensions: false,
  can_manage_organization: false,
};

export type NavItem = {
  href: string;
  label: string;
  visible: (capabilities: Capabilities) => boolean;
};

export type NavGroup = {
  id: string;
  label: string;
  items: NavItem[];
};

export const NAV_GROUPS: NavGroup[] = [
  {
    id: "analyze",
    label: copy.navAnalyze,
    items: [
      {
        href: "/dashboard",
        label: copy.navDashboard,
        visible: (capabilities) => capabilities.can_view_dashboard,
      },
      {
        href: "/variances",
        label: copy.navVariances,
        visible: (capabilities) => capabilities.can_view_dashboard,
      },
    ],
  },
  {
    id: "plan",
    label: copy.navPlan,
    items: [
      {
        href: "/scenarios",
        label: copy.navScenarios,
        visible: (capabilities) => capabilities.can_create_scenario,
      },
    ],
  },
  {
    id: "data",
    label: copy.navData,
    items: [
      {
        href: "/imports",
        label: copy.navImports,
        visible: (capabilities) => capabilities.can_import,
      },
    ],
  },
  {
    id: "assist",
    label: copy.navAssist,
    items: [
      {
        href: "/copilot",
        label: copy.navCopilot,
        visible: (capabilities) => capabilities.can_use_copilot,
      },
    ],
  },
  {
    id: "admin",
    label: copy.navAdmin,
    items: [
      {
        href: "/settings/organization",
        label: copy.navSettings,
        visible: (capabilities) =>
          capabilities.can_view_dashboard || capabilities.can_manage_organization,
      },
      {
        href: "/settings/dimensions",
        label: copy.navDimensions,
        visible: (capabilities) =>
          capabilities.can_view_dashboard || capabilities.can_manage_dimensions,
      },
      {
        href: "/settings/budget-versions",
        label: copy.navVersions,
        visible: (capabilities) =>
          capabilities.can_view_dashboard || capabilities.can_manage_versions,
      },
      {
        href: "/settings/members",
        label: copy.navMembers,
        visible: (capabilities) => capabilities.can_manage_members,
      },
      {
        href: "/audit",
        label: copy.navAudit,
        visible: (capabilities) => capabilities.can_manage_members,
      },
    ],
  },
  {
    id: "ops",
    label: copy.navOps,
    items: [
      {
        href: "/estado",
        label: copy.navStatus,
        visible: (capabilities) => capabilities.can_view_technical_metrics,
      },
    ],
  },
];

export function visibleNavGroups(capabilities: Capabilities): NavGroup[] {
  return NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => item.visible(capabilities)),
  })).filter((group) => group.items.length > 0);
}

export function personaLabel(persona: string | null | undefined): string {
  if (persona === "budget_owner") {
    return copy.personaBudgetOwner;
  }
  if (persona === "fpna_analyst") {
    return copy.personaAnalyst;
  }
  if (persona === "organization_admin") {
    return copy.personaAdmin;
  }
  if (persona === "platform_operator") {
    return copy.personaOperator;
  }
  return copy.roleLabel;
}
