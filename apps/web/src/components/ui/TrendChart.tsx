import type { BreakdownItem } from "@budgetlens/api-client";

import { Money } from "@/components/ui/Money";
import { Table } from "@/components/ui/Table";
import { VarianceBadge } from "@/components/ui/VarianceBadge";
import { copy } from "@/lib/copy";
import { formatPercent } from "@/lib/format";

function toNumber(amount: string): number {
  const negative = amount.startsWith("-");
  const [whole = "0"] = (negative ? amount.slice(1) : amount).split(".");
  const value = Number.parseInt(whole || "0", 10);
  return negative ? -value : value;
}

export function TrendChart({ items, currency }: { items: BreakdownItem[]; currency: string }) {
  if (items.length === 0) {
    return null;
  }
  const values = items.flatMap((item) => [
    toNumber(item.metrics.budget_amount),
    toNumber(item.metrics.actual_amount),
  ]);
  const min = Math.min(0, ...values);
  const max = Math.max(0, ...values);
  const span = max - min || 1;
  const width = 640;
  const height = 180;
  const step = items.length > 1 ? width / (items.length - 1) : width;
  function point(index: number, amount: string) {
    const x = index * step;
    const y = height - ((toNumber(amount) - min) / span) * height;
    return `${x},${y}`;
  }
  const budget = items.map((item, index) => point(index, item.metrics.budget_amount)).join(" ");
  const actual = items.map((item, index) => point(index, item.metrics.actual_amount)).join(" ");

  return (
    <div>
      <svg
        role="img"
        aria-label={copy.trendTitle}
        viewBox={`0 0 ${width} ${height}`}
        className="h-48 w-full"
      >
        <polyline
          fill="none"
          stroke="var(--bl-brand-700)"
          strokeDasharray="6 4"
          strokeWidth="2"
          points={budget}
        />
        <polyline fill="none" stroke="var(--bl-brand-600)" strokeWidth="2" points={actual} />
      </svg>
      <p className="mt-2 text-xs text-secondary">
        {copy.chartBudgetSeries} · {copy.chartActualSeries} · {currency}
      </p>
      <Table caption={copy.chartAccessible} className="mt-4">
        <thead>
          <tr className="border-b border-border text-secondary">
            <th className="py-2 pr-4 font-medium">{copy.periodLabel}</th>
            <th className="py-2 pr-4 text-right font-medium">{copy.columnBudget}</th>
            <th className="py-2 pr-4 text-right font-medium">{copy.columnActual}</th>
            <th className="py-2 pr-4 text-right font-medium">{copy.columnVariance}</th>
            <th className="py-2 font-medium">{copy.columnFavorability}</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.group_id} className="border-b border-border last:border-0">
              <td className="py-2 pr-4">{item.group_code}</td>
              <td className="py-2 pr-4 text-right">
                <Money value={item.metrics.budget_amount} currency={currency} />
              </td>
              <td className="py-2 pr-4 text-right">
                <Money value={item.metrics.actual_amount} currency={currency} />
              </td>
              <td className="py-2 pr-4 text-right">
                <Money value={item.metrics.variance_amount} currency={currency} />{" "}
                {formatPercent(item.metrics.variance_percent)}
              </td>
              <td className="py-2">
                <VarianceBadge value={item.metrics.favorability} />
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </div>
  );
}
