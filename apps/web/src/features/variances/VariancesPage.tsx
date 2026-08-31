"use client";

import Link from "next/link";
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
import { favorabilityLabel, formatMoney, formatPercent } from "@/lib/format";
import { queryFromFilters } from "@/lib/query-from-filters";

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
  const groupBy = filters.accountId
    ? "cost_center"
    : filters.departmentId
      ? "account"
      : "department";
  const [summary, setSummary] = useState<VarianceSummary | null>(null);
  const [items, setItems] = useState<BreakdownItem[]>([]);
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">("idle");
  const crumbs = [
    { href: withPathFilters("/dashboard", filters), label: copy.breadcrumbHome },
    filters.departmentId
      ? {
          href: withPathFilters("/variances", { ...filters, accountId: "", costCenterId: "" }),
          label: labelFor(catalog.departments, filters.departmentId, copy.filterDepartment),
        }
      : null,
    filters.accountId
      ? {
          href: withPathFilters("/variances", { ...filters, costCenterId: "" }),
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
    const auth = { token: userId, organizationId };
    setStatus("loading");
    void Promise.all([
      getVarianceSummary(apiBaseUrl(), auth, query),
      getVarianceBreakdown(apiBaseUrl(), auth, query, groupBy),
    ])
      .then(([nextSummary, nextItems]) => {
        setSummary(nextSummary.data);
        setItems(nextItems.data.items);
        setStatus("ready");
      })
      .catch(() => setStatus("error"));
  }, [groupBy, organizationId, query, userId]);

  const currency = summary?.scope.currency ?? selectedOrganization?.functional_currency ?? "MXN";

  return (
    <CapabilityGate allowed={capabilities.can_view_dashboard} hasSession={hasSession}>
      <nav aria-label="breadcrumb" className="text-sm text-secondary">
        <ol className="flex flex-wrap gap-2">
          {crumbs.map((crumb, index) => (
            <li key={crumb.href} className="flex items-center gap-2">
              {index > 0 ? <span aria-hidden="true">/</span> : null}
              {index === crumbs.length - 1 ? (
                <span className="text-primary">{crumb.label}</span>
              ) : (
                <Link className="text-brand-600" href={crumb.href}>
                  {crumb.label}
                </Link>
              )}
            </li>
          ))}
        </ol>
      </nav>
      <div className="mt-4">
        <PageHeader
          title={copy.variancesTitle}
          description={copy.variancesDescription}
          actions={
            <Button
              variant="secondary"
              disabled={!query || status !== "ready"}
              onClick={() => {
                if (!query || !userId || !organizationId) return;
                void createExport(
                  apiBaseUrl(),
                  { token: userId, organizationId },
                  query,
                  groupBy,
                ).then((result) =>
                  downloadAuthorized(
                    exportDownloadUrl(apiBaseUrl(), result.data.id),
                    { token: userId, organizationId },
                    result.data.filename,
                  ),
                );
              }}
            >
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
      />
      {status === "loading" ? (
        <p className="mt-6 text-sm text-secondary">{copy.loadingFigures}</p>
      ) : null}
      {status === "error" ? <p className="mt-6 text-sm text-danger">{copy.figuresError}</p> : null}
      {status === "ready" && summary ? (
        <section className="mt-6 rounded-surface border border-border bg-surface p-6">
          <p className="text-sm text-secondary">
            {formatMoney(summary.metrics.variance_amount, currency)} ·{" "}
            {favorabilityLabel(summary.metrics.favorability)} ·{" "}
            {formatPercent(summary.metrics.variance_percent)}
          </p>
          <ul className="mt-4 space-y-2">
            {items.map((item) => (
              <li key={item.group_id}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between rounded-control px-2 py-2 text-left text-sm hover:bg-canvas"
                  onClick={() => {
                    if (groupBy === "department")
                      update({ departmentId: item.group_id, accountId: "", costCenterId: "" });
                    if (groupBy === "account")
                      update({ accountId: item.group_id, costCenterId: "" });
                    if (groupBy === "cost_center") update({ costCenterId: item.group_id });
                  }}
                >
                  <span>
                    {item.group_code} — {item.group_name}
                  </span>
                  <span>
                    {formatMoney(item.metrics.variance_amount, currency)} ·{" "}
                    {favorabilityLabel(item.metrics.favorability)}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <EmptyState title={copy.emptyFigures} detail={copy.emptyFiguresHint} />
      )}
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
