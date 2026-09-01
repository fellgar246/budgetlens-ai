import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export function Table({
  caption,
  children,
  className,
}: {
  caption?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("overflow-x-auto", className)}>
      <table className="min-w-full text-left text-sm">
        {caption ? <caption className="sr-only">{caption}</caption> : null}
        {children}
      </table>
    </div>
  );
}

export function SortButton({
  label,
  active,
  direction,
  onClick,
}: {
  label: string;
  active: boolean;
  direction: "asc" | "desc";
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className="inline-flex h-8 items-center gap-1 font-medium text-secondary"
      aria-sort={active ? (direction === "asc" ? "ascending" : "descending") : "none"}
      onClick={onClick}
    >
      {label}
      <span aria-hidden="true">{active ? (direction === "asc" ? "↑" : "↓") : ""}</span>
    </button>
  );
}
