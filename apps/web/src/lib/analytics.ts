export const PRODUCT_EVENTS = [
  "import_started",
  "import_validated",
  "import_applied",
  "dashboard_filtered",
  "variance_drilled_down",
  "export_created",
  "copilot_question_completed",
  "scenario_previewed",
] as const;

export type ProductEventName = (typeof PRODUCT_EVENTS)[number];

export type ProductEvent = {
  name: ProductEventName;
  properties: Record<string, string | number | boolean>;
  at: string;
};

const STORAGE_KEY = "budgetlens.telemetry";
const SENSITIVE_KEYS = /amount|value|content|prompt|question|message|email|filename|row|text/i;

export function trackEvent(
  name: ProductEventName,
  properties: Record<string, string | number | boolean> = {},
): void {
  const safe: Record<string, string | number | boolean> = {};
  for (const [key, value] of Object.entries(properties)) {
    if (SENSITIVE_KEYS.test(key)) {
      continue;
    }
    if (typeof value === "string" && value.length > 80) {
      continue;
    }
    safe[key] = value;
  }
  const event: ProductEvent = { name, properties: safe, at: new Date().toISOString() };
  if (typeof window === "undefined") {
    return;
  }
  const existing = readTelemetry();
  existing.push(event);
  window.sessionStorage.setItem(STORAGE_KEY, JSON.stringify(existing.slice(-100)));
  window.dispatchEvent(new CustomEvent("budgetlens-telemetry", { detail: event }));
}

export function readTelemetry(): ProductEvent[] {
  if (typeof window === "undefined") {
    return [];
  }
  try {
    const raw = window.sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as ProductEvent[]) : [];
  } catch {
    return [];
  }
}

export function filterDimensionNames(filters: {
  departmentId?: string;
  accountId?: string;
  costCenterId?: string;
}): string[] {
  const names: string[] = [];
  if (filters.departmentId) names.push("department");
  if (filters.accountId) names.push("account");
  if (filters.costCenterId) names.push("cost_center");
  return names;
}
