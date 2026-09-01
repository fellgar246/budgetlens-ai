import { Button } from "@/components/ui/Button";
import { copy } from "@/lib/copy";

export function Pagination({
  from,
  to,
  hasMore,
  onPrevious,
  onNext,
  canPrevious,
}: {
  from: number;
  to: number;
  hasMore: boolean;
  onPrevious?: () => void;
  onNext?: () => void;
  canPrevious?: boolean;
}) {
  return (
    <nav aria-label={copy.paginationLabel} className="mt-4 flex flex-wrap items-center justify-between gap-3">
      <p className="text-sm text-secondary">
        {from}–{to} {copy.paginationRange}
        {hasMore ? "" : `. ${copy.noMoreResults}`}
      </p>
      <div className="flex gap-2">
        {onPrevious ? (
          <Button variant="secondary" disabled={!canPrevious} onClick={onPrevious}>
            {copy.previousPage}
          </Button>
        ) : null}
        {onNext ? (
          <Button variant="secondary" disabled={!hasMore} onClick={onNext}>
            {copy.nextPage}
          </Button>
        ) : null}
      </div>
    </nav>
  );
}
