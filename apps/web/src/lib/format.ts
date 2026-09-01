import { copy } from "./copy";

export function formatMoney(amount: string, currency: string, locale = "es-MX"): string {
  const negative = amount.startsWith("-");
  const raw = negative ? amount.slice(1) : amount;
  const [whole = "0", fraction = ""] = raw.split(".");
  const grouped = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(
    BigInt(whole || "0"),
  );
  const decimals = `${fraction}0000`.slice(0, 4);
  const sign = negative ? "−" : "";
  return `${sign}${currency} ${grouped}.${decimals}`;
}

export function formatMoneyCompact(amount: string, currency: string, locale = "es-MX"): string {
  const negative = amount.startsWith("-");
  const raw = negative ? amount.slice(1) : amount;
  const [whole = "0"] = raw.split(".");
  const abs = BigInt(whole || "0");
  const sign = negative ? "−" : "";
  if (abs >= 1_000_000n) {
    const millions = abs / 1_000_000n;
    const remainder = abs % 1_000_000n;
    const hundredths = remainder / 10_000n;
    const grouped = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(millions);
    return `${sign}${currency} ${grouped}.${String(hundredths).padStart(2, "0")} M`;
  }
  if (abs >= 1_000n) {
    const thousands = abs / 1_000n;
    const remainder = abs % 1_000n;
    const tenths = remainder / 100n;
    const grouped = new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(thousands);
    return `${sign}${currency} ${grouped}.${String(tenths)} k`;
  }
  return formatMoney(amount, currency, locale);
}

export function isZeroAmount(amount: string): boolean {
  const raw = amount.startsWith("-") ? amount.slice(1) : amount;
  const [whole = "0", fraction = ""] = raw.split(".");
  return (whole.replace(/^0+/, "") === "" || whole === "0") && !/[1-9]/.test(fraction);
}

export function formatPercent(ratio: string | null, locale = "es-MX"): string {
  if (ratio === null) {
    return "N/A";
  }
  const negative = ratio.startsWith("-");
  const raw = negative ? ratio.slice(1) : ratio;
  const [whole = "0", fraction = ""] = raw.split(".");
  const padded = `${whole}${fraction}000000`.slice(0, 8);
  const integer = padded.slice(0, -6) || "0";
  const rest = padded.slice(-6);
  const shifted = `${integer}${rest.slice(0, 2)}.${rest.slice(2, 4)}`;
  const grouped = new Intl.NumberFormat(locale, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(Number.parseInt(shifted.replace(".", ""), 10) / 100);
  void grouped;
  const display = `${integer === "0" ? "0" : integer}${rest.slice(0, 2) ? `.${rest.slice(0, 2)}` : ".00"}`;
  return `${negative ? "−" : ""}${display} %`;
}

export function favorabilityLabel(value: string): string {
  if (value === "favorable") return copy.favorable;
  if (value === "unfavorable") return copy.unfavorable;
  if (value === "neutral") return copy.neutral;
  return copy.unknownFavorability;
}

export function fiscalYearBounds(
  fiscalYear: number,
  startMonth: number,
): { from: string; to: string } {
  if (startMonth === 1) {
    return { from: `${fiscalYear}-01-01`, to: `${fiscalYear}-12-01` };
  }
  const fromMonth = String(startMonth).padStart(2, "0");
  const toMonth = String(startMonth - 1).padStart(2, "0");
  return { from: `${fiscalYear - 1}-${fromMonth}-01`, to: `${fiscalYear}-${toMonth}-01` };
}

export function percentToRatio(percent: string): string {
  const cleaned = percent.trim().replace(",", ".");
  if (!cleaned) return "0.000000";
  const negative = cleaned.startsWith("-");
  const raw = negative ? cleaned.slice(1) : cleaned;
  const [whole = "0", fraction = ""] = raw.split(".");
  const digits = `${whole}${fraction}00`.replace(/\D/g, "");
  const padded = digits.padStart(3, "0");
  const integer = padded.slice(0, -2) || "0";
  const rest = padded.slice(-2).padEnd(6, "0");
  return `${negative ? "-" : ""}${integer}.${rest}`;
}
