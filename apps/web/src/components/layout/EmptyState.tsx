import type { ReactNode } from "react";

export function EmptyState({
  title,
  detail,
  action,
}: {
  title: string;
  detail: string;
  action?: ReactNode;
}) {
  return (
    <section className="mt-8 rounded-surface border border-border bg-surface p-6">
      <h2 className="text-lg font-semibold text-primary">{title}</h2>
      <p className="mt-2 text-sm text-secondary">{detail}</p>
      {action ? <div className="mt-4">{action}</div> : null}
    </section>
  );
}
