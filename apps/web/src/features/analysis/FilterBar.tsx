"use client";

import { useEffect, useState } from "react";
import type { Account, BudgetVersion, CostCenter, Department } from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { Combobox } from "@/components/ui/Combobox";
import { DatePeriodRange } from "@/components/ui/DatePeriodRange";
import { Drawer } from "@/components/ui/Drawer";
import { Select } from "@/components/ui/Select";
import type { AnalysisFilters, GroupByDimension } from "@/lib/analysis-filters";
import { filterDimensionNames, trackEvent } from "@/lib/analytics";
import { copy } from "@/lib/copy";

export function FilterBar({
  filters,
  versions,
  departments,
  accounts,
  costCenters,
  onChange,
  onReset,
  showGroupBy = false,
  eventName,
}: {
  filters: AnalysisFilters;
  versions: BudgetVersion[];
  departments: Department[];
  accounts: Account[];
  costCenters: CostCenter[];
  onChange: (patch: Partial<AnalysisFilters>) => void;
  onReset: () => void;
  showGroupBy?: boolean;
  eventName?: "dashboard_filtered";
}) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [draft, setDraft] = useState(filters);

  useEffect(() => {
    setDraft(filters);
  }, [filters]);

  function emit(patch: Partial<AnalysisFilters>) {
    const next = { ...filters, ...patch };
    if (eventName) {
      trackEvent(eventName, {
        dimensions: filterDimensionNames(next).join(",") || "none",
      });
    }
    onChange(patch);
  }

  const chips = [
    filters.departmentId
      ? `${copy.filterDepartment}: ${labelFor(departments, filters.departmentId)}`
      : null,
    filters.accountId ? `${copy.filterAccount}: ${labelFor(accounts, filters.accountId)}` : null,
    filters.costCenterId
      ? `${copy.filterCostCenter}: ${labelFor(costCenters, filters.costCenterId)}`
      : null,
  ].filter((item): item is string => item !== null);

  return (
    <div className="sticky top-14 z-10 mt-6 rounded-surface border border-border bg-surface p-4 md:top-16">
      <div className="grid gap-3 lg:grid-cols-4">
        <Select
          label={copy.filterVersion}
          value={filters.budgetVersionId}
          onChange={(event) => emit({ budgetVersionId: event.target.value })}
        >
          <option value="">{copy.chooseVersion}</option>
          {versions.map((version) => (
            <option key={version.id} value={version.id}>
              {version.name} · {version.fiscal_year}
            </option>
          ))}
        </Select>
        <div className="lg:col-span-2">
          <DatePeriodRange
            from={filters.periodFrom}
            to={filters.periodTo}
            onChange={(patch) => emit(patch)}
          />
        </div>
        <div className="hidden lg:block">
          {showGroupBy ? (
            <Select
              label={copy.groupByLabel}
              value={filters.groupBy}
              onChange={(event) => emit({ groupBy: event.target.value as GroupByDimension })}
            >
              <option value="department">{copy.groupByDepartment}</option>
              <option value="account">{copy.groupByAccount}</option>
              <option value="cost_center">{copy.groupByCostCenter}</option>
            </Select>
          ) : (
            <Select
              label={copy.filterSort}
              value={filters.sort}
              onChange={(event) =>
                emit({
                  sort: event.target.value === "variance_amount" ? "variance_amount" : "unfavorable",
                })
              }
            >
              <option value="unfavorable">{copy.sortUnfavorable}</option>
              <option value="variance_amount">{copy.sortVariance}</option>
            </Select>
          )}
        </div>
      </div>
      <div className="mt-3 hidden grid-cols-3 gap-3 lg:grid">
        <DimensionField
          label={copy.filterDepartment}
          value={filters.departmentId}
          items={departments}
          onChange={(departmentId) => emit({ departmentId })}
        />
        <DimensionField
          label={copy.filterAccount}
          value={filters.accountId}
          items={accounts}
          onChange={(accountId) => emit({ accountId })}
        />
        <DimensionField
          label={copy.filterCostCenter}
          value={filters.costCenterId}
          items={costCenters}
          onChange={(costCenterId) => emit({ costCenterId })}
        />
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {chips.map((chip) => (
          <span key={chip} className="rounded-pill bg-canvas px-3 py-1 text-xs text-primary">
            {chip}
          </span>
        ))}
        <Button variant="link" className="lg:hidden" onClick={() => setDrawerOpen(true)}>
          {copy.openFilters}
          {chips.length ? ` (${chips.length})` : ""}
        </Button>
        <Button variant="link" onClick={onReset}>
          {copy.resetFilters}
        </Button>
      </div>
      <Drawer
        open={drawerOpen}
        title={copy.openFilters}
        onClose={() => setDrawerOpen(false)}
        footer={
          <div className="flex gap-2">
            <Button
              className="flex-1"
              onClick={() => {
                emit(draft);
                setDrawerOpen(false);
              }}
            >
              {copy.applyFilters}
              {chips.length ? ` (${chips.length})` : ""}
            </Button>
            <Button
              variant="secondary"
              onClick={() => {
                onReset();
                setDrawerOpen(false);
              }}
            >
              {copy.resetFilters}
            </Button>
          </div>
        }
      >
        <div className="space-y-3">
          <DimensionField
            label={copy.filterDepartment}
            value={draft.departmentId}
            items={departments}
            onChange={(departmentId) => setDraft((current) => ({ ...current, departmentId }))}
          />
          <DimensionField
            label={copy.filterAccount}
            value={draft.accountId}
            items={accounts}
            onChange={(accountId) => setDraft((current) => ({ ...current, accountId }))}
          />
          <DimensionField
            label={copy.filterCostCenter}
            value={draft.costCenterId}
            items={costCenters}
            onChange={(costCenterId) => setDraft((current) => ({ ...current, costCenterId }))}
          />
        </div>
      </Drawer>
    </div>
  );
}

function DimensionField({
  label,
  value,
  items,
  onChange,
}: {
  label: string;
  value: string;
  items: Array<{ id: string; code: string; name: string }>;
  onChange: (value: string) => void;
}) {
  if (items.length > 10) {
    return <Combobox label={label} value={value} items={items} onChange={onChange} />;
  }
  return (
    <Select label={label} value={value} onChange={(event) => onChange(event.target.value)}>
      <option value="">{copy.chooseAll}</option>
      {items.map((item) => (
        <option key={item.id} value={item.id}>
          {item.code} — {item.name}
        </option>
      ))}
    </Select>
  );
}

function labelFor(items: Array<{ id: string; code: string; name: string }>, id: string) {
  const match = items.find((item) => item.id === id);
  return match ? `${match.code} — ${match.name}` : id;
}
