import { copy } from "@/lib/copy";

export type EvidenceRecordView = {
  id: string;
  tool: string;
  label: string;
  data: Record<string, unknown>;
};

const METRIC_LABELS: Record<string, string> = {
  budget_amount: copy.kpiBudget,
  actual_amount: copy.kpiActual,
  variance_amount: copy.kpiVariance,
  variance_percent: copy.kpiVariancePct,
  baseline: copy.baselineLabel,
  result: copy.previewImpact,
};

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function asEvidenceRecords(items: Array<Record<string, unknown>>): EvidenceRecordView[] {
  return items.slice(0, 8).map((item, index) => {
    const data = isRecord(item.data) ? item.data : {};
    return {
      id: typeof item.id === "string" ? item.id : `ev_${index + 1}`,
      tool: typeof item.tool === "string" ? item.tool : "",
      label: typeof item.label === "string" ? item.label : "",
      data,
    };
  });
}

export function scopeLines(scope: Record<string, unknown>): string[] {
  const lines: string[] = [];
  if (scope.fiscal_year !== undefined && scope.fiscal_year !== "") {
    lines.push(`${copy.fiscalYearLabel}: ${String(scope.fiscal_year)}`);
  }
  if (typeof scope.period_from === "string" && typeof scope.period_to === "string") {
    lines.push(`${copy.periodRange}: ${scope.period_from} – ${scope.period_to}`);
  }
  if (typeof scope.currency === "string" && scope.currency) {
    lines.push(`${copy.currencyLabel}: ${scope.currency}`);
  }
  if (typeof scope.budget_version_id === "string" && scope.budget_version_id) {
    lines.push(`${copy.filterVersion}: ${scope.budget_version_id.slice(0, 8)}`);
  }
  return lines;
}

const MONEY_KEYS = new Set([
  "budget_amount",
  "actual_amount",
  "variance_amount",
  "baseline",
  "result",
]);

export function metricPairs(
  data: Record<string, unknown>,
): Array<{ label: string; value: string; money: boolean }> {
  const metrics = isRecord(data.metrics) ? data.metrics : data;
  const keys = [
    "budget_amount",
    "actual_amount",
    "variance_amount",
    "variance_percent",
    "favorability",
    "variance_state",
    "baseline",
    "result",
  ];
  const pairs: Array<{ label: string; value: string; money: boolean }> = [];
  for (const key of keys) {
    const value = metrics[key];
    if (value === undefined || value === null) {
      continue;
    }
    pairs.push({
      label: METRIC_LABELS[key] ?? key.replaceAll("_", " "),
      value: String(value),
      money: MONEY_KEYS.has(key),
    });
  }
  return pairs.slice(0, 6);
}

export function itemSummaries(
  data: Record<string, unknown>,
  limit = 5,
): Array<{ name: string; variance: string }> {
  const items = data.items;
  if (!Array.isArray(items)) {
    return [];
  }
  return items.slice(0, limit).flatMap((item) => {
    if (!isRecord(item)) {
      return [];
    }
    const name = String(item.group_name ?? item.group_code ?? "");
    const variance = typeof item.variance_amount === "string" ? item.variance_amount : "";
    if (!name && !variance) {
      return [];
    }
    return [{ name, variance }];
  });
}
