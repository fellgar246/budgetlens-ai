"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  archiveScenario,
  createScenario,
  getScenario,
  patchScenario,
  previewScenario,
  type ScenarioPreview,
} from "@budgetlens/api-client";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { DatePeriodRange } from "@/components/ui/DatePeriodRange";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Input } from "@/components/ui/Input";
import { Money } from "@/components/ui/Money";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/ui/Table";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { EmptyState } from "@/components/layout/EmptyState";
import { PageHeader } from "@/components/layout/PageHeader";
import { useCatalogOptions } from "@/features/analysis/useCatalogOptions";
import { useSession } from "@/features/session/SessionProvider";
import { trackEvent } from "@/lib/analytics";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";
import { fiscalYearBounds, formatMoney, percentToRatio } from "@/lib/format";
import { draftsFromSavedRules, type ScenarioRuleDraft } from "@/lib/scenario-rules";

type RuleDraft = ScenarioRuleDraft;

const EMPTY_RULE: RuleDraft = {
  operation: "percentage_change",
  value: "5",
  departmentId: "",
  periodFrom: "",
  periodTo: "",
};

export function ScenarioBuilderPage({ scenarioId }: { scenarioId?: string }) {
  const router = useRouter();
  const { userId, organizationId, selectedOrganization, capabilities } = useSession();
  const { versions, departments } = useCatalogOptions();
  const [name, setName] = useState("");
  const [baseline, setBaseline] = useState("");
  const [rules, setRules] = useState<RuleDraft[]>([{ ...EMPTY_RULE }]);
  const [preview, setPreview] = useState<ScenarioPreview | null>(null);
  const [error, setError] = useState<Error | string | null>(null);
  const [saved, setSaved] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [status, setStatus] = useState("saved");
  const [phrase, setPhrase] = useState("");
  const [suggestion, setSuggestion] = useState<RuleDraft | null>(null);
  const hasSession = Boolean(userId && organizationId);
  const version = versions.find((item) => item.id === baseline);
  const bounds = version
    ? fiscalYearBounds(version.fiscal_year, selectedOrganization?.fiscal_year_start_month ?? 1)
    : null;
  const currency = selectedOrganization?.functional_currency ?? "MXN";

  const payload = useMemo(
    () =>
      rules.map((rule, index) => ({
        sequence: index + 1,
        operation: rule.operation,
        value:
          rule.operation === "percentage_change"
            ? percentToRatio(rule.value)
            : `${rule.value}.0000`,
        scope: {
          period_from: rule.periodFrom || bounds?.from,
          period_to: rule.periodTo || bounds?.to,
          account_ids: [],
          department_ids: rule.departmentId ? [rule.departmentId] : [],
          cost_center_ids: [],
        },
      })),
    [bounds, rules],
  );

  useEffect(() => {
    if (!scenarioId || !userId || !organizationId) return;
    void getScenario(apiBaseUrl(), sessionAuth(userId, organizationId), scenarioId).then(
      (result) => {
        setName(result.data.name);
        setBaseline(result.data.budget_version_id ?? "");
        setStatus(result.data.status);
        const loadedBounds = fiscalYearBounds(
          result.data.fiscal_year,
          selectedOrganization?.fiscal_year_start_month ?? 1,
        );
        setRules(draftsFromSavedRules(result.data.rules, loadedBounds.from, loadedBounds.to));
      },
    );
  }, [organizationId, scenarioId, selectedOrganization?.fiscal_year_start_month, userId]);

  useEffect(() => {
    if (!version || !bounds || !userId || !organizationId) return;
    const timer = window.setTimeout(() => {
      void previewScenario(apiBaseUrl(), sessionAuth(userId, organizationId), {
        fiscal_year: version.fiscal_year,
        period_from: bounds.from,
        period_to: bounds.to,
        budget_version_id: version.id,
        baseline_type: "budget",
        department_ids: rules.flatMap((rule) => (rule.departmentId ? [rule.departmentId] : [])),
        rules: payload,
      })
        .then((result) => {
          setPreview(result.data);
          trackEvent("scenario_previewed", {
            operation: rules[0]?.operation ?? "percentage_change",
          });
        })
        .catch((err: Error) => setError(err));
    }, 400);
    return () => window.clearTimeout(timer);
  }, [bounds, organizationId, payload, rules, userId, version]);

  function sentence(rule: RuleDraft) {
    const dept = departments.find((item) => item.id === rule.departmentId);
    const numeric = Number.parseFloat(rule.value.replace(",", ".")) || 0;
    const direction =
      rule.operation === "absolute_change"
        ? copy.adjustRule
        : numeric < 0
          ? copy.decreaseRule
          : copy.increaseRule;
    const amount =
      rule.operation === "percentage_change" ? `${Math.abs(numeric)}%` : String(Math.abs(numeric));
    const scope = dept ? `en ${dept.name}` : copy.allAreas;
    return `${direction} ${amount} ${scope}, ${rule.periodFrom || bounds?.from}–${rule.periodTo || bounds?.to}`;
  }

  return (
    <CapabilityGate allowed={capabilities.can_create_scenario} hasSession={hasSession}>
      <PageHeader title={copy.scenariosTitle} description={copy.scenariosDescription} />
      <p className="mt-2 text-xs text-secondary">
        {saved ? copy.savedState : dirty ? copy.unsavedChanges : copy.previewUnsaved}
      </p>
      <div className="mt-6 grid gap-6 xl:grid-cols-[400px_minmax(0,1fr)]">
        <section className="space-y-4 rounded-surface border border-border bg-surface p-6">
          <Input
            label={copy.scenarioName}
            value={name}
            onChange={(event) => {
              setName(event.target.value);
              setDirty(true);
              setSaved(false);
            }}
          />
          <Select
            label={copy.baselineLabel}
            value={baseline}
            onChange={(event) => {
              setBaseline(event.target.value);
              setDirty(true);
            }}
          >
            <option value="">{copy.chooseVersion}</option>
            {versions.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </Select>
          <Input
            label={copy.suggestRule}
            hint={copy.suggestHint}
            value={phrase}
            onChange={(event) => setPhrase(event.target.value)}
          />
          <Button
            variant="secondary"
            onClick={() => {
              const match = phrase.match(/(-?\d+(?:[.,]\d+)?)\s*%/);
              const dept = departments.find((item) =>
                phrase.toLowerCase().includes(item.name.toLowerCase()),
              );
              setSuggestion({
                ...EMPTY_RULE,
                value: match?.[1]?.replace(",", ".") ?? "5",
                departmentId: dept?.id ?? "",
                periodFrom: bounds?.from ?? "",
                periodTo: bounds?.to ?? "",
              });
            }}
          >
            {copy.suggestRule}
          </Button>
          {suggestion ? (
            <Alert title={copy.ruleSentence} tone="info">
              <p>{sentence(suggestion)}</p>
              <div className="mt-3 flex gap-2">
                <Button
                  onClick={() => {
                    setRules((current) => [...current, suggestion]);
                    setSuggestion(null);
                    setDirty(true);
                  }}
                >
                  {copy.confirmSuggestedRule}
                </Button>
                <Button variant="ghost" onClick={() => setSuggestion(null)}>
                  {copy.discardSuggestion}
                </Button>
              </div>
            </Alert>
          ) : null}
          {rules.map((rule, index) => (
            <div key={index} className="space-y-3 rounded-surface border border-border p-3">
              <p className="text-sm text-primary">{sentence(rule)}</p>
              <Select
                label={copy.operationLabel}
                value={rule.operation}
                onChange={(event) => {
                  const value = event.target.value as RuleDraft["operation"];
                  setRules((current) =>
                    current.map((item, itemIndex) =>
                      itemIndex === index ? { ...item, operation: value } : item,
                    ),
                  );
                  setDirty(true);
                }}
              >
                <option value="percentage_change">{copy.operationPercent}</option>
                <option value="absolute_change">{copy.operationAbsolute}</option>
              </Select>
              <Input
                label={copy.ruleValue}
                value={rule.value}
                onChange={(event) => {
                  setRules((current) =>
                    current.map((item, itemIndex) =>
                      itemIndex === index ? { ...item, value: event.target.value } : item,
                    ),
                  );
                  setDirty(true);
                }}
              />
              <Select
                label={copy.filterDepartment}
                value={rule.departmentId}
                onChange={(event) => {
                  setRules((current) =>
                    current.map((item, itemIndex) =>
                      itemIndex === index ? { ...item, departmentId: event.target.value } : item,
                    ),
                  );
                  setDirty(true);
                }}
              >
                <option value="">{copy.chooseAll}</option>
                {departments.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.code} — {item.name}
                  </option>
                ))}
              </Select>
              <DatePeriodRange
                from={rule.periodFrom || bounds?.from || ""}
                to={rule.periodTo || bounds?.to || ""}
                onChange={(patch) => {
                  setRules((current) =>
                    current.map((item, itemIndex) =>
                      itemIndex === index
                        ? {
                            ...item,
                            periodFrom: patch.periodFrom ?? item.periodFrom,
                            periodTo: patch.periodTo ?? item.periodTo,
                          }
                        : item,
                    ),
                  );
                  setDirty(true);
                }}
              />
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="ghost"
                  disabled={index === 0}
                  onClick={() =>
                    setRules((current) => {
                      const next = [...current];
                      const previous = next[index - 1];
                      const currentRule = next[index];
                      if (!previous || !currentRule) return current;
                      next[index - 1] = currentRule;
                      next[index] = previous;
                      return next;
                    })
                  }
                >
                  {copy.moveUp}
                </Button>
                <Button
                  variant="ghost"
                  disabled={index === rules.length - 1}
                  onClick={() =>
                    setRules((current) => {
                      const next = [...current];
                      const following = next[index + 1];
                      const currentRule = next[index];
                      if (!following || !currentRule) return current;
                      next[index + 1] = currentRule;
                      next[index] = following;
                      return next;
                    })
                  }
                >
                  {copy.moveDown}
                </Button>
                <Button
                  variant="ghost"
                  disabled={rules.length === 1}
                  onClick={() =>
                    setRules((current) => current.filter((_, itemIndex) => itemIndex !== index))
                  }
                >
                  {copy.removeRule}
                </Button>
              </div>
            </div>
          ))}
          <Button
            variant="secondary"
            onClick={() => setRules((current) => [...current, { ...EMPTY_RULE }])}
          >
            {copy.addRule}
          </Button>
          <Button
            disabled={
              !preview || !name || !version || !userId || !organizationId || status === "archived"
            }
            onClick={() => {
              if (!version || !userId || !organizationId) return;
              const auth = sessionAuth(userId, organizationId);
              const request = scenarioId
                ? patchScenario(apiBaseUrl(), auth, scenarioId, { name, rules: payload })
                : createScenario(apiBaseUrl(), auth, {
                    name,
                    baseline_type: "budget",
                    budget_version_id: version.id,
                    fiscal_year: version.fiscal_year,
                    rules: payload,
                  });
              void request
                .then((result) => {
                  setSaved(true);
                  setDirty(false);
                  setStatus(result.data.status);
                  router.push(`/scenarios/detail/?id=${result.data.id}`);
                })
                .catch((err: Error) => setError(err));
            }}
          >
            {scenarioId ? copy.updateScenario : copy.saveScenario}
          </Button>
          {scenarioId ? (
            <Button
              variant="secondary"
              disabled={status === "archived" || !userId || !organizationId}
              onClick={() => {
                if (!userId || !organizationId || !scenarioId) return;
                void archiveScenario(apiBaseUrl(), sessionAuth(userId, organizationId), scenarioId)
                  .then(() => {
                    setStatus("archived");
                    router.push("/scenarios/");
                  })
                  .catch((err: Error) => setError(err));
              }}
            >
              {copy.archiveScenario}
            </Button>
          ) : null}
        </section>
        <section className="rounded-surface border border-border bg-surface p-6">
          <ErrorBanner error={error} />
          {preview ? (
            <>
              <h2 className="text-lg font-semibold text-primary">{copy.comparisonTitle}</h2>
              <p className="mt-3 text-sm text-secondary" aria-live="polite">
                {copy.impactTotal}: {formatMoney(preview.result, currency)} · {copy.baselineLabel}:{" "}
                {formatMoney(preview.baseline, currency)}
              </p>
              <Table className="mt-4" caption={copy.chartAccessible}>
                <thead>
                  <tr className="border-b border-border text-secondary">
                    <th className="py-2 font-medium">{copy.periodLabel}</th>
                    <th className="py-2 text-right font-medium">{copy.baselineLabel}</th>
                    <th className="py-2 text-right font-medium">{copy.previewTitle}</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.monthly.map((item) => (
                    <tr key={item.period} className="border-b border-border">
                      <td className="py-2">{item.period}</td>
                      <td className="py-2 text-right">
                        <Money value={item.baseline} currency={currency} />
                      </td>
                      <td className="py-2 text-right">
                        <Money value={item.result} currency={currency} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </Table>
            </>
          ) : (
            <EmptyState title={copy.previewTitle} detail={copy.emptyScenarioImpact} />
          )}
        </section>
      </div>
    </CapabilityGate>
  );
}
