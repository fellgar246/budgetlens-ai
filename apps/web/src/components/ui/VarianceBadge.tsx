import { favorabilityLabel } from "@/lib/format";
import { cn } from "@/lib/cn";

const ICONS: Record<string, string> = {
  favorable: "↑",
  unfavorable: "↓",
  neutral: "—",
  unknown: "?",
};

const COLORS: Record<string, string> = {
  favorable: "text-success",
  unfavorable: "text-danger",
  neutral: "text-secondary",
  unknown: "text-secondary",
};

export function VarianceBadge({ value }: { value: string }) {
  const icon = ICONS[value] ?? ICONS.unknown;
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs font-medium", COLORS[value])}>
      <span aria-hidden="true">{icon}</span>
      <span>{favorabilityLabel(value)}</span>
    </span>
  );
}
