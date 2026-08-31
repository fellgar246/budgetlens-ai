"use client";

import { useState } from "react";

import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusPage } from "@/features/status/StatusPage";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";

export function OpsPage({ requireOperator = false }: { requireOperator?: boolean }) {
  const { capabilities, userId } = useSession();
  const [traceId, setTraceId] = useState("");
  const allowed = requireOperator ? capabilities.can_view_technical_metrics : true;

  return (
    <CapabilityGate
      allowed={allowed}
      hasSession={Boolean(userId) || !requireOperator}
      needsSession={requireOperator}
    >
      <PageHeader title={copy.opsTitle} description={copy.opsDescription} />
      <div className="mt-8">
        <StatusPage embedded />
      </div>
      <section className="mx-auto mt-8 w-full max-w-3xl rounded-surface border border-border bg-surface p-6">
        <h2 className="text-lg font-semibold text-primary">{copy.traceLookup}</h2>
        <p className="mt-2 text-sm text-secondary">{copy.traceLookupHint}</p>
        <label className="mt-4 flex flex-col gap-1 text-xs">
          <span className="font-medium text-secondary">{copy.traceLabel}</span>
          <input
            className="h-10 rounded-control border border-border px-3 text-sm"
            value={traceId}
            onChange={(event) => setTraceId(event.target.value.trim())}
          />
        </label>
        {traceId ? (
          <p className="mt-3 text-sm text-primary">
            {copy.traceLabel}: {traceId}
          </p>
        ) : null}
      </section>
    </CapabilityGate>
  );
}
