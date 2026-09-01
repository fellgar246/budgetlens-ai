import { VarianceBadge } from "@/components/ui/VarianceBadge";
import { Money } from "@/components/ui/Money";
import { copy } from "@/lib/copy";
import { formatPercent, isZeroAmount } from "@/lib/format";

export function Variance({
  amount,
  percent,
  favorability,
  currency,
  budgetAmount,
}: {
  amount: string;
  percent: string | null;
  favorability: string;
  currency: string;
  budgetAmount?: string;
}) {
  const budgetZero = budgetAmount ? isZeroAmount(budgetAmount) : percent === null;
  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <Money value={amount} currency={currency} />
      <span
        className="text-secondary"
        title={budgetZero ? copy.zeroBudgetHint : undefined}
      >
        {budgetZero ? copy.zeroBudgetPercent : formatPercent(percent)}
      </span>
      <VarianceBadge value={favorability} />
    </span>
  );
}
