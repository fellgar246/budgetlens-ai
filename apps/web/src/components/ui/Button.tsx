import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
};

const variants: Record<Variant, string> = {
  primary: "bg-brand-700 text-white hover:bg-[#0f2436] disabled:bg-[#98a2b3] disabled:text-white",
  secondary: "border border-border bg-surface text-primary hover:bg-canvas disabled:text-secondary",
  ghost: "text-brand-600 hover:bg-canvas disabled:text-secondary",
};

export function Button({ className, variant = "primary", type = "button", ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex h-10 min-w-10 items-center justify-center rounded-control px-4 text-sm font-medium transition-colors duration-150",
        variants[variant],
        className,
      )}
      {...props}
    />
  );
}
