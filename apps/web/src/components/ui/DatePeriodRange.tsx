import { copy } from "@/lib/copy";

export function DatePeriodRange({
  from,
  to,
  onChange,
}: {
  from: string;
  to: string;
  onChange: (patch: { periodFrom?: string; periodTo?: string }) => void;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-secondary">{copy.filterPeriodFrom}</span>
        <input
          type="month"
          className="h-10 rounded-control border border-border bg-white px-3 text-sm"
          value={from.length >= 7 ? from.slice(0, 7) : ""}
          onChange={(event) =>
            onChange({ periodFrom: event.target.value ? `${event.target.value}-01` : "" })
          }
        />
      </label>
      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-secondary">{copy.filterPeriodTo}</span>
        <input
          type="month"
          className="h-10 rounded-control border border-border bg-white px-3 text-sm"
          value={to.length >= 7 ? to.slice(0, 7) : ""}
          onChange={(event) =>
            onChange({ periodTo: event.target.value ? `${event.target.value}-01` : "" })
          }
        />
      </label>
    </div>
  );
}
