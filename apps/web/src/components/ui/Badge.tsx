import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

const tones: Record<string, string> = {
  neutral: "bg-[#eaecf0] text-primary",
  success: "bg-[#ecfdf3] text-success",
  warning: "bg-[#fffaeb] text-warning",
  danger: "bg-[#fef3f2] text-danger",
  info: "bg-[#eff8ff] text-info",
};

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: keyof typeof tones;
}) {
  return (
    <span
      className={cn(
        "inline-flex h-6 items-center rounded-pill px-2 text-xs font-medium",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}
