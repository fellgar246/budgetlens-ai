import type { ReactNode, SelectHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  hint?: ReactNode;
  error?: string;
};

export function Select({ id, label, hint, error, className, children, ...props }: SelectProps) {
  const selectId = id ?? props.name ?? label.replace(/\s+/g, "-").toLowerCase();
  const hintId = hint ? `${selectId}-hint` : undefined;
  const errorId = error ? `${selectId}-error` : undefined;
  return (
    <label className="flex min-w-0 flex-col gap-1 text-xs" htmlFor={selectId}>
      <span className="font-medium text-secondary">{label}</span>
      <select
        id={selectId}
        aria-invalid={error ? true : undefined}
        aria-describedby={[hintId, errorId].filter(Boolean).join(" ") || undefined}
        className={cn(
          "h-10 rounded-control border bg-white px-3 text-sm text-primary",
          error ? "border-danger" : "border-border",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <span className="min-h-5 text-xs text-secondary" id={hintId}>
        {error ? (
          <span id={errorId} className="text-danger">
            {error}
          </span>
        ) : (
          hint
        )}
      </span>
    </label>
  );
}
