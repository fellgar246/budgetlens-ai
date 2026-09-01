import { copy } from "@/lib/copy";
import { cn } from "@/lib/cn";

export function Skeleton({ className, label }: { className?: string; label?: string }) {
  return (
    <div
      aria-busy="true"
      aria-label={label ?? copy.loadingLabel}
      className={cn("animate-pulse rounded bg-[#eaecf0]", className)}
    />
  );
}

export function DashboardSkeleton() {
  return (
    <div className="mt-6 space-y-6" aria-busy="true" aria-label={copy.loadingFigures}>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Skeleton key={index} className="h-28" />
        ))}
      </div>
      <Skeleton className="h-56" />
      <Skeleton className="h-40" />
    </div>
  );
}
