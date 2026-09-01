import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger" | "link";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  loading?: boolean;
};

const variants: Record<Variant, string> = {
  primary: "bg-brand-700 text-white hover:bg-[#0f2436] disabled:bg-[#98a2b3] disabled:text-white",
  secondary: "border border-border bg-surface text-primary hover:bg-canvas disabled:text-secondary",
  ghost: "text-brand-600 hover:bg-canvas disabled:text-secondary",
  danger: "bg-danger text-white hover:bg-[#912018] disabled:bg-[#fda29b] disabled:text-white",
  link: "h-auto min-h-10 px-0 text-info underline-offset-2 hover:underline disabled:text-secondary",
};

export function Button({
  className,
  variant = "primary",
  type = "button",
  loading = false,
  disabled,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      aria-busy={loading || undefined}
      disabled={disabled || loading}
      className={cn(
        "inline-flex h-10 min-w-10 items-center justify-center rounded-control px-4 text-sm font-medium transition-colors duration-150",
        variants[variant],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
