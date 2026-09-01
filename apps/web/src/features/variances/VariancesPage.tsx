"use client";

import { useEffect, useMemo, useState } from "react";
import {
  createExport,
  downloadAuthorized,
  exportDownloadUrl,
  getVarianceBreakdown,
  getVarianceSummary,
  type BreakdownItem,
  type VarianceSummary,
} from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { Breadcrumb } from "@/components/ui/Breadcrumb";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Money } from "@/components/ui/Money";
import { Pagination } from "@/components/ui/Pagination";
import { Table } from "@/components/ui/Table";
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
import { withPathFilters, type GroupByDimension } from "@/lib/analysis-filters";
import { trackEvent } from "@/lib/analytics";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";
import { formatPercent } from "@/lib/format";
import { queryFromFilters } from "@/lib/query-from-filters";

const PAGE_SIZE = 50;

export function VariancesPage() {
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
  const groupBy: GroupByDimension = filters.groupBy;
  const [summary, setSummary] = useState<VarianceSummary | null>(null);
  const [items, setItems] = useState<BreakdownItem[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const [error, setError] = useState<Error | string | null>(null);
  const [exportOpen, setExportOpen] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [pageFrom, setPageFrom] = useState(1);

  const crumbs = [
    { href: withPathFilters("/dashboard", filters), label: copy.breadcrumbHome },
    { href: withPathFilters("/variances", { ...filters, departmentId: "", accountId: "", costCenterId: "", groupBy: "department" }), label: copy.allAreas },
    filters.departmentId
      ? {
          href: withPathFilters("/variances", {
            ...filters,
            accountId: "",
            costCenterId: "",
            groupBy: "account",
          }),
          label: labelFor(catalog.departments, filters.departmentId, copy.filterDepartment),
        }
      : null,
    filters.accountId
      ? {
          href: withPathFilters("/variances", { ...filters, costCenterId: "", groupBy: "cost_center" }),
          label: labelFor(catalog.accounts, filters.accountId, copy.filterAccount),
        }
      : null,
    filters.costCenterId
      ? {
          href: withPathFilters("/variances", filters),
          label: labelFor(catalog.costCenters, filters.costCenterId, copy.filterCostCenter),
        }
      : null,
  ].filter((item): item is { href: string; label: string } => item !== null);

  useEffect(() => {
    if (!userId || !organizationId || !query) {
      setStatus("idle");
      return;
    }
    const auth = sessionAuth(userId, organizationId);
    setStatus(items.length ? "ready" : "loading");
    void Promise.all([
      getVarianceSummary(apiBaseUrl(), auth, query),
      getVarianceBreakdown(apiBaseUrl(), auth, query, groupBy, {
        sort: filters.sort === "unfavorable" ? "absolute_variance" : "variance_amount",
        direction: "desc",
        cursor: filters.cursor || undefined,
        limit: PAGE_SIZE,
      }),
    ])
      .then(([nextSummary, nextItems]) => {
        setSummary(nextSummary.data);
        setItems(nextItems.data.items);
        setHasMore(nextItems.data.page.has_more);
        setNextCursor(nextItems.data.page.next_cursor);
        setPageFrom(filters.cursor ? pageFrom : 1);
        setStatus("ready");
        setError(null);
      })
      .catch((err: Error) => {
        setError(err);
        setStatus("error");
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.cursor, filters.sort, groupBy, organizationId, query, userId]);

  const currency = summary?.scope.currency ?? selectedOrganization?.functional_currency ?? "MXN";
  const filtered = Boolean(filters.departmentId || filters.accountId || filters.costCenterId);

  function drill(item: BreakdownItem) {
    trackEvent("variance_drilled_down", { group_by: groupBy });
    if (groupBy === "department") {
      update({ departmentId: item.group_id, accountId: "", costCenterId: "", groupBy: "account" });
    } else if (groupBy === "account") {
      update({ accountId: item.group_id, costCenterId: "", groupBy: "cost_center" });
    } else {
      update({ costCenterId: item.group_id });
    }
  }

  return (
    <CapabilityGate allowed={capabilities.can_view_dashboard} hasSession={hasSession}>
      <Breadcrumb items={crumbs} />
      <div className="mt-4">
        <PageHeader
          title={copy.variancesTitle}
          description={copy.variancesDescription}
          actions={
            <Button variant="secondary" disabled={!query || status !== "ready"} onClick={() => setExportOpen(true)}>
              {copy.exportView}
            </Button>
          }
        />
      </div>
      <FilterBar
        filters={filters}
        versions={catalog.versions}
        departments={catalog.departments}
        accounts={catalog.accounts}
        costCenters={catalog.costCenters}
        onChange={update}
        onReset={reset}
        showGroupBy
      />
      <p className="mt-3 text-xs text-secondary">{copy.sortOrderLabel}</p>
      {status === "loading" ? <p className="mt-6 text-sm text-secondary">{copy.loadingFigures}</p> : null}
      {status === "error" ? <ErrorBanner error={error ?? copy.figuresError} onRetry={() => update({})} /> : null}
      {status === "ready" && summary && items.length > 0 ? (
        <section className="mt-6 rounded-surface border border-border bg-surface p-4 md:p-6">
          <p className="text-sm text-secondary">
            <Variance
              amount={summary.metrics.variance_amount}
              percent={summary.metrics.variance_percent}
              favorability={summary.metrics.favorability}
              currency={currency}
              budgetAmount={summary.metrics.budget_amount}
            />
          </p>
          <div className="mt-4 hidden md:block">
            <Table caption={copy.variancesTitle}>
              <thead className="sticky top-0 bg-surface">
                <tr className="border-b border-border text-secondary">
                  <th className="sticky left-0 bg-surface py-2 pr-4 font-medium">{copy.columnDimension}</th>
                  <th className="py-2 pr-4 text-right font-medium">{copy.columnBudget}</th>
                  <th className="py-2 pr-4 text-right font-medium">{copy.columnActual}</th>
                  <th className="py-2 pr-4 text-right font-medium">{copy.columnVariance}</th>
                  <th className="py-2 pr-4 text-right font-medium">{copy.columnPercent}</th>
                  <th className="py-2 font-medium">{copy.columnFavorability}</th>
                  <th className="py-2 font-medium">{copy.openDetail}</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.group_id} className="border-b border-border last:border-0">
                    <td className="sticky left-0 bg-surface py-2 pr-4">
                      {item.group_code} — {item.group_name}
                    </td>
                    <td className="py-2 pr-4 text-right">
                      <Money value={item.metrics.budget_amount} currency={currency} />
                    </td>
                    <td className="py-2 pr-4 text-right">
                      <Money value={item.metrics.actual_amount} currency={currency} />
                    </td>
                    <td className="py-2 pr-4 text-right">
                      <Money value={item.metrics.variance_amount} currency={currency} />
                    </td>
                    <td className="py-2 pr-4 text-right">{formatPercent(item.metrics.variance_percent)}</td>
                    <td className="py-2">
                      <VarianceBadge value={item.metrics.favorability} />
                    </td>
                    <td className="py-2">
                      <Button variant="link" onClick={() => drill(item)}>
                        {copy.openDetail}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </Table>
          </div>
          <ul className="mt-4 space-y-3 md:hidden">
            {items.map((item) => (
              <li key={item.group_id} className="rounded-surface border border-border p-3">
                <p className="font-medium text-primary">
                  {item.group_code} — {item.group_name}
                </p>
                <p className="mt-1 text-sm">
                  <Money value={item.metrics.actual_amount} currency={currency} /> ·{" "}
                  <Money value={item.metrics.variance_amount} currency={currency} /> ·{" "}
                  <VarianceBadge value={item.metrics.favorability} />
                </p>
                {expanded === item.group_id ? (
                  <p className="mt-2 text-sm text-secondary">
                    {copy.columnBudget}: <Money value={item.metrics.budget_amount} currency={currency} /> ·{" "}
                    {formatPercent(item.metrics.variance_percent)}
                  </p>
                ) : null}
                <div className="mt-2 flex gap-3">
                  <Button
                    variant="link"
                    onClick={() => setExpanded(expanded === item.group_id ? null : item.group_id)}
                  >
                    {expanded === item.group_id ? copy.collapseRow : copy.expandRow}
                  </Button>
                  <Button variant="link" onClick={() => drill(item)}>
                    {copy.openDetail}
                  </Button>
                </div>
              </li>
            ))}
          </ul>
          <Pagination
            from={pageFrom}
            to={pageFrom + items.length - 1}
            hasMore={hasMore}
            canPrevious={Boolean(filters.cursor)}
            onPrevious={() => update({ cursor: "" })}
            onNext={() => nextCursor && update({ cursor: nextCursor })}
          />
        </section>
      ) : status === "ready" || status === "idle" ? (
        <EmptyState
          title={filtered ? copy.emptyFiltered : copy.emptyFigures}
          detail={filtered ? copy.emptyFilteredHint : copy.emptyFiguresHint}
        />
      ) : null}
      <ExportDialog
        open={exportOpen}
        scope={`${currency} · ${copy.groupByLabel}: ${groupBy} · ${copy.filterSort}: ${filters.sort}`}
        onClose={() => setExportOpen(false)}
        onConfirm={() => {
          if (!query || !userId || !organizationId) return;
          void createExport(apiBaseUrl(), sessionAuth(userId, organizationId), query, groupBy).then(
            (result) => {
              trackEvent("export_created", { group_by: groupBy });
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

function labelFor(
  items: Array<{ id: string; code: string; name: string }>,
  id: string,
  fallback: string,
) {
  const match = items.find((item) => item.id === id);
  return match ? `${match.code} — ${match.name}` : fallback;
}
