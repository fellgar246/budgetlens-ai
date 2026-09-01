"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  createExport,
  downloadAuthorized,
  exportDownloadUrl,
  getTopUnfavorable,
  getVarianceBreakdown,
  getVarianceSummary,
  type BreakdownItem,
  type VarianceSummary,
} from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { VarianceBadge } from "@/components/ui/VarianceBadge";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { EmptyState } from "@/components/layout/EmptyState";
import { PageHeader } from "@/components/layout/PageHeader";
import { FilterBar } from "@/features/analysis/FilterBar";
import { useCatalogOptions } from "@/features/analysis/useCatalogOptions";
import { useAnalysisFilters } from "@/features/session/useAnalysisFilters";
import { useSession } from "@/features/session/SessionProvider";
import { withPathFilters } from "@/lib/analysis-filters";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";
import { formatMoney, formatPercent } from "@/lib/format";
import { queryFromFilters } from "@/lib/query-from-filters";

export function DashboardPage() {
  const { userId, organizationId, selectedOrganization, capabilities } = useSession();
  const { filters, update, reset } = useAnalysisFilters();
  const catalog = useCatalogOptions();
  const hasSession = Boolean(userId && organizationId);
  const query = useMemo(
    () =>
      queryFromFilters(
        filters,
        catalog.versions,
        selectedOrganization?.fiscal_year_start_month ?? 1,
      ),
    [catalog.versions, filters, selectedOrganization?.fiscal_year_start_month],
  );
  const [summary, setSummary] = useState<VarianceSummary | null>(null);
  const [trend, setTrend] = useState<BreakdownItem[]>([]);
  const [top, setTop] = useState<BreakdownItem[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "empty" | "ready">("idle");
  const [error, setError] = useState<Error | string | null>(null);

  useEffect(() => {
    if (!userId || !organizationId || !query) {
      setSummary(null);
      setTrend([]);
      setTop([]);
      setStatus("idle");
      return;
    }
    const auth = sessionAuth(userId, organizationId);
    setStatus("loading");
    void Promise.all([
      getVarianceSummary(apiBaseUrl(), auth, query),
      getVarianceBreakdown(apiBaseUrl(), auth, query, "period"),
      getTopUnfavorable(apiBaseUrl(), auth, query, "account"),
    ])
      .then(([nextSummary, nextTrend, nextTop]) => {
        setSummary(nextSummary.data);
        setTrend(nextTrend.data.items);
        setTop(nextTop.data.items);
        const inactive =
          nextSummary.data.metrics.variance_state === "no_activity" &&
          nextSummary.data.metrics.budget_amount === "0.0000";
        setStatus(inactive ? "empty" : "ready");
      })
      .catch((err: Error) => {
        setError(err);
        setStatus("error");
      });
  }, [organizationId, query, userId]);

  const currency = summary?.scope.currency ?? selectedOrganization?.functional_currency ?? "MXN";

  return (
    <CapabilityGate allowed={capabilities.can_view_dashboard} hasSession={hasSession}>
      <PageHeader
        eyebrow={copy.appName}
        title={copy.dashboardTitle}
        description={copy.dashboardDescription}
        actions={
          <Button
            variant="secondary"
            disabled={!query || status !== "ready"}
            title={status === "ready" ? copy.exportView : copy.exportDisabled}
            onClick={() => {
              if (!query || !userId || !organizationId) return;
              void createExport(
                apiBaseUrl(),
                sessionAuth(userId, organizationId),
                query,
                "account",
              ).then((result) =>
                downloadAuthorized(
                  exportDownloadUrl(apiBaseUrl(), result.data.id),
                  sessionAuth(userId, organizationId),
                  result.data.filename,
                ),
              );
            }}
          >
            {copy.exportView}
          </Button>
        }
      />
      <FilterBar
        filters={filters}
        versions={catalog.versions}
        departments={catalog.departments}
        accounts={catalog.accounts}
        costCenters={catalog.costCenters}
        onChange={update}
        onReset={reset}
      />
      <p className="mt-3 text-xs text-secondary">
        {currency} · {copy.filterSort}:{" "}
        {filters.sort === "unfavorable" ? copy.sortUnfavorable : copy.sortVariance}
      </p>
      {status === "loading" ? (
        <p className="mt-6 text-sm text-secondary">{copy.loadingFigures}</p>
      ) : null}
      {status === "error" ? <ErrorBanner error={error ?? copy.figuresError} /> : null}
      {status === "ready" && summary ? (
        <>
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Kpi
              label={copy.kpiBudget}
              value={formatMoney(summary.metrics.budget_amount, currency)}
            />
            <Kpi
              label={copy.kpiActual}
              value={formatMoney(summary.metrics.actual_amount, currency)}
            />
            <Kpi
              label={copy.kpiVariance}
              value={formatMoney(summary.metrics.variance_amount, currency)}
              hint={<VarianceBadge value={summary.metrics.favorability} />}
            />
            <Kpi
              label={copy.kpiVariancePct}
              value={formatPercent(summary.metrics.variance_percent)}
            />
          </div>
          <section className="mt-8 rounded-surface border border-border bg-surface p-6">
            <h2 className="text-lg font-semibold text-primary">{copy.trendTitle}</h2>
            <ul className="mt-4 space-y-2 text-sm">
              {trend.map((item) => (
                <li key={item.group_id} className="flex justify-between gap-4">
                  <span>{item.group_code}</span>
                  <span>{formatMoney(item.metrics.variance_amount, currency)}</span>
                </li>
              ))}
            </ul>
          </section>
          <section className="mt-6 rounded-surface border border-border bg-surface p-6">
            <h2 className="text-lg font-semibold text-primary">{copy.topUnfavorableTitle}</h2>
            <ul className="mt-4 space-y-2 text-sm">
              {top.map((item) => (
                <li key={item.group_id}>
                  <Link
                    className="text-brand-600"
                    href={withPathFilters("/variances", { ...filters, accountId: item.group_id })}
                  >
                    {item.group_code} — {item.group_name}:{" "}
                    {formatMoney(item.metrics.variance_amount, currency)}
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        </>
      ) : null}
      {status === "empty" || status === "idle" ? (
        <EmptyState
          title={copy.emptyFigures}
          detail={copy.emptyFiguresHint}
          action={
            capabilities.can_import ? (
              <Link className="text-sm font-medium text-brand-600" href="/imports">
                {copy.importToCompare}
              </Link>
            ) : (
              <Link
                className="text-sm font-medium text-brand-600"
                href={withPathFilters("/variances", filters)}
              >
                {copy.navVariances}
              </Link>
            )
          }
        />
      ) : null}
    </CapabilityGate>
  );
}

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string | ReactNode }) {
  return (
    <article className="rounded-surface border border-border bg-surface p-4">
      <p className="text-sm text-secondary">{label}</p>
      <p className="mt-2 text-[32px] font-semibold leading-10 text-primary">{value}</p>
      <div className="mt-1 text-xs text-secondary">{hint ?? copy.vsBudget}</div>
    </article>
  );
}
