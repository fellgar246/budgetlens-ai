import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

const tones: Record<string, string> = {
  info: "border-info text-info",
  success: "border-success text-success",
  warning: "border-warning text-warning",
  danger: "border-danger text-danger",
};

export function Alert({
  title,
  children,
  tone = "info",
}: {
  title: string;
  children?: ReactNode;
  tone?: keyof typeof tones;
}) {
  return (
    <div role="status" className={cn("rounded-surface border bg-surface p-4", tones[tone])}>
      <p className="text-sm font-medium">{title}</p>
      {children ? <div className="mt-1 text-sm text-secondary">{children}</div> : null}
    </div>
  );
}
