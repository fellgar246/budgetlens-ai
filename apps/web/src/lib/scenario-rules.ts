export type ScenarioRuleDraft = {
  operation: "percentage_change" | "absolute_change";
  value: string;
  departmentId: string;
  periodFrom: string;
  periodTo: string;
};

export function ratioToPercent(ratio: string): string {
  const cleaned = ratio.trim();
  if (!cleaned) return "0";
  const negative = cleaned.startsWith("-");
  const raw = (negative ? cleaned.slice(1) : cleaned).replace(",", ".");
  const [whole = "0", fraction = ""] = raw.split(".");
  const frac = fraction.replace(/\D/g, "").padEnd(6, "0").slice(0, 6);
  const scaled = `${whole.replace(/\D/g, "") || "0"}${frac}`.replace(/^0+/, "") || "0";
  const padded = scaled.padStart(5, "0");
  const integer = padded.slice(0, -4).replace(/^0+/, "") || "0";
  const decimals = padded.slice(-4).replace(/0+$/, "");
  return `${negative ? "-" : ""}${decimals ? `${integer}.${decimals}` : integer}`;
}

export function stripMoneyScale(value: string): string {
  const cleaned = value.trim();
  if (!cleaned.includes(".")) return cleaned || "0";
  return cleaned.replace(/(\.\d*?)0+$/, "$1").replace(/\.$/, "") || "0";
}

export function draftsFromSavedRules(
  rules: Array<Record<string, unknown>>,
  fallbackFrom: string,
  fallbackTo: string,
): ScenarioRuleDraft[] {
  if (rules.length === 0) {
    return [
      {
        operation: "percentage_change",
        value: "5",
        departmentId: "",
        periodFrom: fallbackFrom,
        periodTo: fallbackTo,
      },
    ];
  }
  return rules.map((rule) => {
    const scope =
      rule.scope && typeof rule.scope === "object" ? (rule.scope as Record<string, unknown>) : {};
    const departmentIds = Array.isArray(scope.department_ids) ? scope.department_ids : [];
    const operation =
      rule.operation === "absolute_change" ? "absolute_change" : "percentage_change";
    const rawValue = String(rule.value ?? "0");
    return {
      operation,
      value:
        operation === "percentage_change" ? ratioToPercent(rawValue) : stripMoneyScale(rawValue),
      departmentId: String(departmentIds[0] ?? ""),
      periodFrom: String(scope.period_from ?? fallbackFrom),
      periodTo: String(scope.period_to ?? fallbackTo),
    };
  });
}
