"use client";

import { useState } from "react";
import {
  createConversation,
  sendConversationMessage,
  type CopilotMessage,
} from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { PageHeader } from "@/components/layout/PageHeader";
import { useCatalogOptions } from "@/features/analysis/useCatalogOptions";
import { useAnalysisFilters } from "@/features/session/useAnalysisFilters";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { queryFromFilters } from "@/lib/query-from-filters";

export function CopilotPage() {
  const { userId, organizationId, selectedOrganization, capabilities } = useSession();
  const { filters } = useAnalysisFilters();
  const catalog = useCatalogOptions();
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<CopilotMessage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const hasSession = Boolean(userId && organizationId);
  const query = queryFromFilters(
    filters,
    catalog.versions,
    selectedOrganization?.fiscal_year_start_month ?? 1,
  );
  const context = query
    ? {
        fiscal_year: query.fiscal_year,
        period_from: query.period_from,
        period_to: query.period_to,
        budget_version_id: query.budget_version_id,
        department_ids: query.department_id ? [query.department_id] : [],
        account_ids: query.account_id ? [query.account_id] : [],
        currency: selectedOrganization?.functional_currency,
      }
    : {};
  const contextChips = [
    selectedOrganization
      ? `${copy.currencyLabel}: ${selectedOrganization.functional_currency}`
      : null,
    filters.budgetVersionId
      ? `${copy.filterVersion}: ${catalog.versions.find((item) => item.id === filters.budgetVersionId)?.name ?? filters.budgetVersionId}`
      : null,
    query ? `${copy.filterPeriodFrom}: ${query.period_from}` : null,
    query ? `${copy.filterPeriodTo}: ${query.period_to}` : null,
    filters.departmentId
      ? `${copy.filterDepartment}: ${catalog.departments.find((item) => item.id === filters.departmentId)?.code ?? filters.departmentId}`
      : null,
  ].filter((item): item is string => item !== null);

  return (
    <CapabilityGate allowed={capabilities.can_use_copilot} hasSession={hasSession}>
      <PageHeader title={copy.copilotTitle} description={copy.copilotDescription} />
      <section className="mt-6 rounded-surface border border-border bg-surface p-6">
        <h2 className="text-sm font-medium text-secondary">{copy.contextTitle}</h2>
        <ul className="mt-3 flex flex-wrap gap-2">
          {contextChips.length === 0 ? (
            <li className="rounded-full bg-canvas px-3 py-1 text-xs text-secondary">
              {copy.chooseOrganization}
            </li>
          ) : (
            contextChips.map((chip) => (
              <li key={chip} className="rounded-full bg-canvas px-3 py-1 text-xs text-primary">
                {chip}
              </li>
            ))
          )}
        </ul>
        <label className="mt-6 flex flex-col gap-1 text-xs">
          <span className="font-medium text-secondary">{copy.askCopilot}</span>
          <textarea
            className="min-h-24 rounded-control border border-border px-3 py-2 text-sm"
            value={question}
            placeholder={copy.copilotPlaceholder}
            onChange={(event) => setQuestion(event.target.value)}
          />
        </label>
        <div className="mt-4">
          <Button
            type="button"
            disabled={!question.trim() || !query || busy || !userId || !organizationId}
            onClick={() => {
              if (!userId || !organizationId || !query) return;
              setBusy(true);
              setError(null);
              const auth = { token: userId, organizationId };
              void createConversation(apiBaseUrl(), auth, { title: question.slice(0, 80), context })
                .then((conversation) =>
                  sendConversationMessage(apiBaseUrl(), auth, conversation.data.id, {
                    content: question,
                    context,
                  }),
                )
                .then((result) => {
                  setAnswer(result.data);
                  setEvidenceOpen(false);
                })
                .catch((err: Error) => setError(err.message))
                .finally(() => setBusy(false));
            }}
          >
            {copy.askCopilot}
          </Button>
        </div>
        {error ? <p className="mt-4 text-sm text-danger">{error}</p> : null}
        {answer ? (
          <div className="mt-6 space-y-3">
            <p className="text-sm text-primary">{answer.answer}</p>
            {answer.limitations.map((item) => (
              <p key={item} className="text-sm text-secondary">
                {item}
              </p>
            ))}
            <Button variant="ghost" onClick={() => setEvidenceOpen((current) => !current)}>
              {evidenceOpen ? copy.hideEvidence : copy.viewEvidence}
            </Button>
            {evidenceOpen ? (
              <div className="rounded-surface border border-border p-4">
                <h3 className="text-sm font-semibold text-primary">{copy.evidenceTitle}</h3>
                {answer.evidence.length === 0 ? (
                  <p className="mt-2 text-sm text-secondary">{copy.evidenceEmpty}</p>
                ) : (
                  <ul className="mt-3 space-y-2 text-xs text-secondary">
                    {answer.evidence.map((item) => (
                      <li key={String(item.id)}>
                        {String(item.tool)} · {String(item.label)}
                      </li>
                    ))}
                  </ul>
                )}
                <ul className="mt-3 space-y-1 text-xs text-secondary">
                  {contextChips.map((chip) => (
                    <li key={chip}>{chip}</li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>
    </CapabilityGate>
  );
}
