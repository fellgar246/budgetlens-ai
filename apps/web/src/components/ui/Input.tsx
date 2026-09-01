import type { InputHTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/cn";

type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  label: string;
  hint?: ReactNode;
  error?: string;
};

export function Input({ id, label, hint, error, className, ...props }: InputProps) {
  const inputId = id ?? props.name ?? label.replace(/\s+/g, "-").toLowerCase();
  const hintId = hint ? `${inputId}-hint` : undefined;
  const errorId = error ? `${inputId}-error` : undefined;
  return (
    <label className="flex min-w-0 flex-col gap-1 text-xs" htmlFor={inputId}>
      <span className="font-medium text-secondary">{label}</span>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={[hintId, errorId].filter(Boolean).join(" ") || undefined}
        className={cn(
          "h-10 rounded-control border bg-white px-3 text-sm text-primary",
          error ? "border-danger" : "border-border",
          className,
        )}
        {...props}
      />
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
