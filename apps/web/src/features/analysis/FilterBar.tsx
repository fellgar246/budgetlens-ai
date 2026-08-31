"use client";

import type { Account, BudgetVersion, CostCenter, Department } from "@budgetlens/api-client";

import type { AnalysisFilters } from "@/lib/analysis-filters";
import { copy } from "@/lib/copy";

export function FilterBar({
  filters,
  versions,
  departments,
  accounts,
  costCenters,
  onChange,
  onReset,
}: {
  filters: AnalysisFilters;
  versions: BudgetVersion[];
  departments: Department[];
  accounts: Account[];
  costCenters: CostCenter[];
  onChange: (patch: Partial<AnalysisFilters>) => void;
  onReset: () => void;
}) {
  return (
    <div className="mt-6 grid gap-3 rounded-surface border border-border bg-surface p-4 md:grid-cols-3 xl:grid-cols-7">
      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-secondary">{copy.filterVersion}</span>
        <select
          className="h-10 rounded-control border border-border px-3 text-sm"
          value={filters.budgetVersionId}
          onChange={(event) => onChange({ budgetVersionId: event.target.value })}
        >
          <option value="">{copy.chooseVersion}</option>
          {versions.map((version) => (
            <option key={version.id} value={version.id}>
              {version.name} · {version.fiscal_year}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-secondary">{copy.filterPeriodFrom}</span>
        <input
          type="month"
          className="h-10 rounded-control border border-border px-3 text-sm"
          value={toMonthInput(filters.periodFrom)}
          onChange={(event) => onChange({ periodFrom: fromMonthInput(event.target.value) })}
        />
      </label>
      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-secondary">{copy.filterPeriodTo}</span>
        <input
          type="month"
          className="h-10 rounded-control border border-border px-3 text-sm"
          value={toMonthInput(filters.periodTo)}
          onChange={(event) => onChange({ periodTo: fromMonthInput(event.target.value) })}
        />
      </label>
      <DimensionSelect
        label={copy.filterDepartment}
        value={filters.departmentId}
        items={departments}
        onChange={(departmentId) => onChange({ departmentId })}
      />
      <DimensionSelect
        label={copy.filterAccount}
        value={filters.accountId}
        items={accounts}
        onChange={(accountId) => onChange({ accountId })}
      />
      <DimensionSelect
        label={copy.filterCostCenter}
        value={filters.costCenterId}
        items={costCenters}
        onChange={(costCenterId) => onChange({ costCenterId })}
      />
      <label className="flex flex-col gap-1 text-xs">
        <span className="font-medium text-secondary">{copy.filterSort}</span>
        <select
          className="h-10 rounded-control border border-border px-3 text-sm"
          value={filters.sort}
          onChange={(event) =>
            onChange({
              sort: event.target.value === "variance_amount" ? "variance_amount" : "unfavorable",
            })
          }
        >
          <option value="unfavorable">{copy.sortUnfavorable}</option>
          <option value="variance_amount">{copy.sortVariance}</option>
        </select>
      </label>
      <div className="xl:col-span-7">
        <button type="button" className="text-sm font-medium text-brand-600" onClick={onReset}>
          {copy.resetFilters}
        </button>
      </div>
    </div>
  );
}

function DimensionSelect({
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
  return (
    <label className="flex flex-col gap-1 text-xs">
      <span className="font-medium text-secondary">{label}</span>
      <select
        className="h-10 rounded-control border border-border px-3 text-sm"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{copy.chooseAll}</option>
        {items.map((item) => (
          <option key={item.id} value={item.id}>
            {item.code} — {item.name}
          </option>
        ))}
      </select>
    </label>
  );
}

function toMonthInput(value: string): string {
  return value.length >= 7 ? value.slice(0, 7) : "";
}

function fromMonthInput(value: string): string {
  return value ? `${value}-01` : "";
}
