"use client";

import { useEffect, useState } from "react";
import { getOpsMetrics, type OpsMetrics } from "@budgetlens/api-client";

import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { PageHeader } from "@/components/layout/PageHeader";
import { StatusPage } from "@/features/status/StatusPage";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";

export function OpsPage({ requireOperator = false }: { requireOperator?: boolean }) {
  const { capabilities, userId } = useSession();
  const [traceId, setTraceId] = useState("");
  const [metrics, setMetrics] = useState<OpsMetrics | null>(null);
  const allowed = requireOperator ? capabilities.can_view_technical_metrics : true;

  useEffect(() => {
    if (!userId || !capabilities.can_view_technical_metrics) {
      return;
    }
    void getOpsMetrics(apiBaseUrl(), { token: userId })
      .then((result) => setMetrics(result.data))
      .catch(() => setMetrics(null));
  }, [capabilities.can_view_technical_metrics, userId]);

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
      {metrics ? (
        <section className="mx-auto mt-8 w-full max-w-3xl rounded-surface border border-border bg-surface p-6">
          <h2 className="text-lg font-semibold text-primary">{copy.metricsTitle}</h2>
          <dl className="mt-4 grid gap-3 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-secondary">{copy.requestsLabel}</dt>
              <dd className="text-primary">
                {metrics.requests.reduce((sum, item) => sum + item.count, 0)}
              </dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-secondary">{copy.jobsTimedOut}</dt>
              <dd className="text-primary">{metrics.jobs.timed_out}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-secondary">{copy.aiRuns}</dt>
              <dd className="text-primary">{metrics.ai.runs}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-secondary">{copy.estimatedCost}</dt>
              <dd className="text-primary">
                {metrics.ai.estimated_cost
                  ? `${metrics.ai.estimated_cost.amount} ${metrics.ai.estimated_cost.currency}`
                  : copy.costNotConfigured}
              </dd>
            </div>
          </dl>
          {metrics.requests.length === 0 ? (
            <p className="mt-3 text-sm text-secondary">{copy.metricsEmpty}</p>
          ) : null}
        </section>
      ) : null}
    </CapabilityGate>
  );
}
