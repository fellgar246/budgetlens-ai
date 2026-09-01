import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function Card({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("rounded-surface border border-border bg-surface p-6", className)}>
      {children}
    </section>
  );
}

export function KpiCard({
  label,
  value,
  hint,
  currency,
  scope,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  currency?: string;
  scope?: string;
}) {
  return (
    <article className="rounded-surface border border-border bg-surface p-4">
      <p className="text-sm text-secondary">{label}</p>
      <div className="mt-2 text-[32px] font-semibold leading-10 text-primary">{value}</div>
      <div className="mt-1 text-xs text-secondary">
        {[currency, scope].filter(Boolean).join(" · ")}
      </div>
      {hint ? <div className="mt-2 text-xs text-secondary">{hint}</div> : null}
    </article>
  );
}
