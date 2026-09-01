import { formatMoney, formatMoneyCompact } from "@/lib/format";

export function Money({
  value,
  currency,
  locale = "es-MX",
  display = "exact",
  sign = "auto",
}: {
  value: string;
  currency: string;
  locale?: string;
  display?: "exact" | "compact";
  sign?: "auto" | "always";
}) {
  const exact = formatMoney(value, currency, locale);
  const shown = display === "compact" ? formatMoneyCompact(value, currency, locale) : exact;
  const prefixed = sign === "always" && !value.startsWith("-") && !shown.startsWith("−") ? `+${shown}` : shown;
  return (
    <span className="tabular-nums" title={exact}>
      <span className="sr-only">{exact}</span>
      <span aria-hidden={display === "compact"}>{prefixed}</span>
    </span>
  );
}
