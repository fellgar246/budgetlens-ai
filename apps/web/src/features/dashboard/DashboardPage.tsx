"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  createExport,
  downloadAuthorized,
  exportDownloadUrl,
  getTopUnfavorable,
  getVarianceBreakdown,
  getVarianceSummary,
  listImports,
  type BreakdownItem,
  type ImportJob,
  type VarianceSummary,
} from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { KpiCard } from "@/components/ui/Card";
import { Money } from "@/components/ui/Money";
import { DashboardSkeleton } from "@/components/ui/Skeleton";
import { TrendChart } from "@/components/ui/TrendChart";
import { Variance } from "@/components/ui/Variance";
import { VarianceBadge } from "@/components/ui/VarianceBadge";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { EmptyState } from "@/components/layout/EmptyState";
import { PageHeader } from "@/components/layout/PageHeader";
import { ExportDialog } from "@/features/analysis/ExportDialog";
import { FilterBar } from "@/features/analysis/FilterBar";
import { useCatalogOptions } from "@/features/analysis/useCatalogOptions";
import { useAnalysisFilters } from "@/features/session/useAnalysisFilters";
import { useSession } from "@/features/session/SessionProvider";
import { withPathFilters } from "@/lib/analysis-filters";
import { trackEvent } from "@/lib/analytics";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";
import { formatPercent } from "@/lib/format";
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
  const [breakdown, setBreakdown] = useState<BreakdownItem[]>([]);
  const [latestImport, setLatestImport] = useState<ImportJob | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error" | "empty" | "ready">("idle");
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<Error | string | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [updatedAt, setUpdatedAt] = useState<string | null>(null);

  function load(isRefresh = false) {
    if (!userId || !organizationId || !query) {
      setSummary(null);
      setTrend([]);
      setTop([]);
      setBreakdown([]);
      setStatus("idle");
      return;
    }
    const auth = sessionAuth(userId, organizationId);
    if (isRefresh && summary) {
      setRefreshing(true);
    } else {
      setStatus("loading");
    }
    void Promise.all([
      getVarianceSummary(apiBaseUrl(), auth, query),
      getVarianceBreakdown(apiBaseUrl(), auth, query, "period"),
      getTopUnfavorable(apiBaseUrl(), auth, query, "account", 5),
      getVarianceBreakdown(apiBaseUrl(), auth, query, "department"),
      listImports(apiBaseUrl(), auth, { limit: 20 }).catch(() => null),
    ])
      .then(([nextSummary, nextTrend, nextTop, nextBreakdown, imports]) => {
        setSummary(nextSummary.data);
        setTrend(nextTrend.data.items);
        setTop(nextTop.data.items);
        setBreakdown(nextBreakdown.data.items);
        const applied = imports?.data.items.find((item) => item.status === "applied") ?? null;
        setLatestImport(applied);
        const inactive =
          nextSummary.data.metrics.variance_state === "no_activity" &&
          nextSummary.data.metrics.budget_amount === "0.0000";
        setStatus(inactive ? "empty" : "ready");
        setUpdatedAt(new Date().toLocaleTimeString("es"));
        setError(null);
      })
      .catch((err: Error) => {
        setError(err);
        if (!summary) {
          setStatus("error");
        }
      })
      .finally(() => setRefreshing(false));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- reload when the query or tenant changes
  }, [organizationId, query, userId]);

  const currency = summary?.scope.currency ?? selectedOrganization?.functional_currency ?? "MXN";
  const periodLabel = query ? `${query.period_from} – ${query.period_to}` : "";
  const filtered = Boolean(filters.departmentId || filters.accountId || filters.costCenterId);

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
            onClick={() => setExportOpen(true)}
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
        eventName="dashboard_filtered"
      />
      <p className="mt-3 text-xs text-secondary">
        {currency} · {copy.filterSort}:{" "}
        {filters.sort === "unfavorable" ? copy.sortOrderLabel : copy.sortVariance}
        {refreshing ? ` · ${copy.updating}` : null}
        {updatedAt ? ` · ${copy.lastDataAt} ${updatedAt}.` : null}
      </p>
      {status === "loading" ? <DashboardSkeleton /> : null}
      {status === "error" ? (
        <ErrorBanner error={error ?? copy.figuresError} onRetry={() => load()} />
      ) : null}
      {status === "ready" && summary ? (
        <>
          <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <KpiCard
              label={copy.kpiBudget}
              value={<Money value={summary.metrics.budget_amount} currency={currency} display="compact" />}
              currency={currency}
              scope={periodLabel}
              hint={copy.vsBudget}
            />
            <KpiCard
              label={copy.kpiActual}
              value={<Money value={summary.metrics.actual_amount} currency={currency} display="compact" />}
              currency={currency}
              scope={periodLabel}
              hint={copy.vsBudget}
            />
            <KpiCard
              label={copy.kpiVariance}
              value={<Money value={summary.metrics.variance_amount} currency={currency} display="compact" />}
              currency={currency}
              scope={periodLabel}
              hint={<VarianceBadge value={summary.metrics.favorability} />}
            />
            <KpiCard
              label={copy.kpiVariancePct}
              value={
                <Variance
                  amount={summary.metrics.variance_amount}
                  percent={summary.metrics.variance_percent}
                  favorability={summary.metrics.favorability}
                  currency={currency}
                  budgetAmount={summary.metrics.budget_amount}
                />
              }
              currency={currency}
              scope={periodLabel}
            />
          </div>
          <section className="mt-8 rounded-surface border border-border bg-surface p-6">
            <h2 className="text-lg font-semibold text-primary">{copy.trendTitle}</h2>
            <TrendChart items={trend} currency={currency} />
          </section>
          <section className="mt-6 rounded-surface border border-border bg-surface p-6">
            <h2 className="text-lg font-semibold text-primary">{copy.topUnfavorableTitle}</h2>
            <ul className="mt-4 space-y-2 text-sm">
              {top.map((item) => (
                <li key={item.group_id}>
                  <Link
                    className="text-brand-600"
                    href={withPathFilters("/variances", {
                      ...filters,
                      accountId: item.group_id,
                      groupBy: "account",
                    })}
                  >
                    {item.group_code} — {item.group_name}:{" "}
                    <Money value={item.metrics.variance_amount} currency={currency} /> ·{" "}
                    <VarianceBadge value={item.metrics.favorability} />
                  </Link>
                </li>
              ))}
            </ul>
          </section>
          <section className="mt-6 rounded-surface border border-border bg-surface p-6">
            <h2 className="text-lg font-semibold text-primary">{copy.breakdownTitle}</h2>
            <ul className="mt-4 space-y-2 text-sm">
              {breakdown.map((item) => (
                <li key={item.group_id} className="flex flex-wrap justify-between gap-3">
                  <Link
                    className="text-brand-600"
                    href={withPathFilters("/variances", {
                      ...filters,
                      departmentId: item.group_id,
                      groupBy: "account",
                    })}
                  >
                    {item.group_code} — {item.group_name}
                  </Link>
                  <span>
                    <Money value={item.metrics.variance_amount} currency={currency} /> ·{" "}
                    {formatPercent(item.metrics.variance_percent)}
                  </span>
                </li>
              ))}
            </ul>
          </section>
          <section className="mt-6 rounded-surface border border-border bg-surface p-6">
            <h2 className="text-lg font-semibold text-primary">{copy.sourceTitle}</h2>
            {latestImport ? (
              <p className="mt-2 text-sm text-secondary">
                {copy.latestImport}: {latestImport.original_filename} · {latestImport.sha256_short}
              </p>
            ) : (
              <p className="mt-2 text-sm text-secondary">{copy.noImportSource}</p>
            )}
            <div className="mt-3 flex flex-wrap gap-3">
              {latestImport ? (
                <Link className="text-sm font-medium text-brand-600" href={`/imports/job/?id=${latestImport.id}`}>
                  {copy.viewImportJob}
                </Link>
              ) : (
                <Link className="text-sm font-medium text-brand-600" href="/imports">
                  {copy.importToCompare}
                </Link>
              )}
              {capabilities.can_manage_members ? (
                <Link className="text-sm font-medium text-brand-600" href="/audit">
                  {copy.viewAudit}
                </Link>
              ) : null}
            </div>
          </section>
        </>
      ) : null}
      {status === "empty" || status === "idle" ? (
        <EmptyState
          title={filtered ? copy.emptyFiltered : copy.emptyFigures}
          detail={filtered ? copy.emptyFilteredHint : copy.emptyActuals}
          action={
            capabilities.can_import ? (
              <Link className="text-sm font-medium text-brand-600" href="/imports/new">
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
      <ExportDialog
        open={exportOpen}
        scope={`${currency} · ${periodLabel} · ${copy.groupByAccount}`}
        onClose={() => setExportOpen(false)}
        onConfirm={() => {
          if (!query || !userId || !organizationId) return;
          void createExport(apiBaseUrl(), sessionAuth(userId, organizationId), query, "account").then(
            (result) => {
              trackEvent("export_created", { group_by: "account" });
              return downloadAuthorized(
                exportDownloadUrl(apiBaseUrl(), result.data.id),
                sessionAuth(userId, organizationId),
                result.data.filename,
              );
            },
          );
          setExportOpen(false);
        }}
      />
    </CapabilityGate>
  );
}
