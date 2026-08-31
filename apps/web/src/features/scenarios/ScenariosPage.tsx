"use client";

import { useState } from "react";
import { createScenario, previewScenario, type ScenarioPreview } from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { EmptyState } from "@/components/layout/EmptyState";
import { PageHeader } from "@/components/layout/PageHeader";
import { useCatalogOptions } from "@/features/analysis/useCatalogOptions";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { fiscalYearBounds, formatMoney, percentToRatio } from "@/lib/format";

export function ScenariosPage() {
  const { userId, organizationId, selectedOrganization, capabilities } = useSession();
  const { versions, departments } = useCatalogOptions();
  const [name, setName] = useState("");
  const [baseline, setBaseline] = useState("");
  const [percent, setPercent] = useState("5");
  const [departmentId, setDepartmentId] = useState("");
  const [preview, setPreview] = useState<ScenarioPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const hasSession = Boolean(userId && organizationId);
  const version = versions.find((item) => item.id === baseline);
  const bounds = version
    ? fiscalYearBounds(version.fiscal_year, selectedOrganization?.fiscal_year_start_month ?? 1)
    : null;

  function rulePayload() {
    return [
      {
        sequence: 1,
        operation: "percentage_change" as const,
        value: percentToRatio(percent),
        scope: {
          period_from: bounds?.from,
          period_to: bounds?.to,
          account_ids: [],
          department_ids: departmentId ? [departmentId] : [],
          cost_center_ids: [],
        },
      },
    ];
  }

  return (
    <CapabilityGate allowed={capabilities.can_create_scenario} hasSession={hasSession}>
      <PageHeader title={copy.scenariosTitle} description={copy.scenariosDescription} />
      <form className="mt-8 grid gap-3 rounded-surface border border-border bg-surface p-6 md:grid-cols-2">
        <label className="flex flex-col gap-1 text-xs">
          <span className="font-medium text-secondary">{copy.scenarioName}</span>
          <input
            className="h-10 rounded-control border border-border px-3 text-sm"
            value={name}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span className="font-medium text-secondary">{copy.baselineLabel}</span>
          <select
            className="h-10 rounded-control border border-border px-3 text-sm"
            value={baseline}
            onChange={(event) => setBaseline(event.target.value)}
          >
            <option value="">{copy.chooseVersion}</option>
            {versions.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span className="font-medium text-secondary">{copy.percentChange}</span>
          <input
            className="h-10 rounded-control border border-border px-3 text-sm"
            value={percent}
            onChange={(event) => setPercent(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span className="font-medium text-secondary">{copy.filterDepartment}</span>
          <select
            className="h-10 rounded-control border border-border px-3 text-sm"
            value={departmentId}
            onChange={(event) => setDepartmentId(event.target.value)}
          >
            <option value="">{copy.chooseAll}</option>
            {departments.map((item) => (
              <option key={item.id} value={item.id}>
                {item.code} — {item.name}
              </option>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap items-end gap-2">
          <Button
            type="button"
            disabled={!version || !bounds || !userId || !organizationId}
            onClick={() => {
              if (!version || !bounds || !userId || !organizationId) return;
              setError(null);
              void previewScenario(
                apiBaseUrl(),
                { token: userId, organizationId },
                {
                  fiscal_year: version.fiscal_year,
                  period_from: bounds.from,
                  period_to: bounds.to,
                  budget_version_id: version.id,
                  baseline_type: "budget",
                  department_ids: departmentId ? [departmentId] : [],
                  rules: rulePayload(),
                },
              )
                .then((result) => setPreview(result.data))
                .catch((err: Error) => setError(err.message));
            }}
          >
            {copy.previewImpact}
          </Button>
          <Button
            type="button"
            variant="secondary"
            disabled={!preview || !name || !version || !userId || !organizationId}
            onClick={() => {
              if (!version || !userId || !organizationId) return;
              void createScenario(
                apiBaseUrl(),
                { token: userId, organizationId },
                {
                  name,
                  baseline_type: "budget",
                  budget_version_id: version.id,
                  fiscal_year: version.fiscal_year,
                  rules: rulePayload(),
                },
              ).catch((err: Error) => setError(err.message));
            }}
          >
            {copy.saveScenario}
          </Button>
        </div>
      </form>
      {error ? <p className="mt-4 text-sm text-danger">{error}</p> : null}
      {preview ? (
        <section className="mt-6 rounded-surface border border-border bg-surface p-6">
          <p className="text-sm text-secondary">
            {copy.baselineLabel}:{" "}
            {formatMoney(preview.baseline, selectedOrganization?.functional_currency ?? "MXN")} ·{" "}
            {copy.previewTitle}:{" "}
            {formatMoney(preview.result, selectedOrganization?.functional_currency ?? "MXN")}
          </p>
          <ul className="mt-4 space-y-1 text-sm">
            {preview.monthly.map((item) => (
              <li key={item.period}>
                {item.period}: {item.baseline} → {item.result}
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <EmptyState title={copy.previewTitle} detail={copy.emptyScenarioImpact} />
      )}
    </CapabilityGate>
  );
}
