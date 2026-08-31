import { copy } from "@/lib/copy";
import { Button } from "@/components/ui/Button";

import type { ComponentState, HealthViewState } from "./types";

type HealthCardProps = {
  state: HealthViewState;
  onRetry: () => void;
  onCopyTrace?: () => void;
  copyFeedback?: string | null;
};

function statusLabel(value: ComponentState): string {
  if (value === "ok") {
    return copy.available;
  }
  if (value === "error") {
    return copy.error;
  }
  return copy.unknown;
}

function StatusDot({ value }: { value: ComponentState }) {
  const color = value === "ok" ? "bg-success" : value === "error" ? "bg-danger" : "bg-secondary";
  return <span aria-hidden="true" className={`inline-block h-2.5 w-2.5 rounded-full ${color}`} />;
}

function formatCheckedAt(value: string): string {
  try {
    return new Intl.DateTimeFormat("es", {
      dateStyle: "short",
      timeStyle: "medium",
    }).format(new Date(value));
  } catch {
    return value;
  }
}

export function HealthCard({ state, onRetry, onCopyTrace, copyFeedback }: HealthCardProps) {
  if (state.kind === "loading") {
    return (
      <section
        aria-busy="true"
        aria-label={copy.checking}
        className="rounded-surface border border-border bg-surface p-6"
      >
        <p className="text-sm font-medium text-secondary">{copy.checking}</p>
        <div className="mt-6 space-y-3">
          <div className="h-7 w-56 animate-pulse rounded bg-[#eaecf0]" />
          <div className="h-4 w-full max-w-md animate-pulse rounded bg-[#eaecf0]" />
          <div className="mt-8 h-12 animate-pulse rounded bg-[#eaecf0]" />
          <div className="h-12 animate-pulse rounded bg-[#eaecf0]" />
        </div>
      </section>
    );
  }

  const isSuccess = state.kind === "success";
  const title = isSuccess ? copy.healthy : state.title;
  const detail = isSuccess ? copy.healthyDetail : state.detail;
  const live = state.live;
  const database = state.database;
  const version = isSuccess ? state.version : state.version;

  return (
    <section aria-live="polite" className="rounded-surface border border-border bg-surface p-6">
      <div className="flex items-start gap-3">
        <StatusDot value={isSuccess ? "ok" : "error"} />
        <div>
          <h2 className="text-lg font-semibold text-primary">{title}</h2>
          <p className="mt-1 text-sm text-secondary">{detail}</p>
        </div>
      </div>

      <dl className="mt-6 divide-y divide-border border-y border-border">
        <div className="flex items-center justify-between py-3">
          <dt className="text-sm font-medium text-primary">{copy.apiLive}</dt>
          <dd className="flex items-center gap-2 text-sm text-secondary">
            <StatusDot value={live} />
            {live === "ok" ? copy.available : statusLabel(live)}
          </dd>
        </div>
        <div className="flex items-center justify-between py-3">
          <dt className="text-sm font-medium text-primary">{copy.database}</dt>
          <dd className="flex items-center gap-2 text-sm text-secondary">
            <StatusDot value={database} />
            {database === "ok" ? copy.ready : statusLabel(database)}
          </dd>
        </div>
        <div className="flex items-center justify-between py-3">
          <dt className="text-sm font-medium text-primary">{copy.version}</dt>
          <dd className="text-sm text-secondary">
            {version
              ? `${version.version} · ${copy.commit} ${version.commit.slice(0, 7)}`
              : copy.unknown}
          </dd>
        </div>
      </dl>

      {state.kind === "error" && state.traceId ? (
        <div className="mt-4 rounded-control border border-border bg-canvas p-3">
          <p className="text-xs font-medium text-secondary">{copy.traceLabel}</p>
          <div className="mt-1 flex flex-wrap items-center justify-between gap-2">
            <code className="break-all text-sm text-primary">{state.traceId}</code>
            {onCopyTrace ? (
              <Button variant="ghost" onClick={onCopyTrace}>
                {copyFeedback ?? copy.copyTrace}
              </Button>
            ) : null}
          </div>
        </div>
      ) : null}

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3">
        <p className="text-xs text-secondary">
          {copy.lastUpdated}: {formatCheckedAt(state.checkedAt)}
        </p>
        <Button variant={isSuccess ? "secondary" : "primary"} onClick={onRetry}>
          {copy.retry}
        </Button>
      </div>
    </section>
  );
}
