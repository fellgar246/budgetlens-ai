"use client";

import { useEffect, useState } from "react";
import {
  createConversation,
  listConversations,
  sendConversationMessage,
  type Conversation,
  type CopilotMessage,
} from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { Drawer } from "@/components/ui/Drawer";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { PageHeader } from "@/components/layout/PageHeader";
import { useCatalogOptions } from "@/features/analysis/useCatalogOptions";
import { useAnalysisFilters } from "@/features/session/useAnalysisFilters";
import { useSession } from "@/features/session/SessionProvider";
import { trackEvent } from "@/lib/analytics";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";
import { queryFromFilters } from "@/lib/query-from-filters";

type ChatItem = {
  role: "user" | "assistant";
  text: string;
  status: "sending" | "analyzing" | "querying" | "completed" | "failed";
  answer?: CopilotMessage;
};

export function CopilotPage() {
  const { userId, organizationId, selectedOrganization, capabilities } = useSession();
  const { filters } = useAnalysisFilters();
  const catalog = useCatalogOptions();
  const [question, setQuestion] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [error, setError] = useState<Error | string | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [listOpen, setListOpen] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<"hidden" | "working" | "long">("hidden");
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

  useEffect(() => {
    if (!userId || !organizationId) return;
    void listConversations(apiBaseUrl(), sessionAuth(userId, organizationId))
      .then((result) => setConversations(result.data.items))
      .catch(() => setConversations([]));
  }, [organizationId, userId]);

  useEffect(() => {
    if (!busy) {
      setProgress("hidden");
      return;
    }
    const first = window.setTimeout(() => setProgress("working"), 1000);
    const second = window.setTimeout(() => setProgress("long"), 10000);
    return () => {
      window.clearTimeout(first);
      window.clearTimeout(second);
    };
  }, [busy]);

  const contextChips = [
    selectedOrganization ? `${copy.currencyLabel}: ${selectedOrganization.functional_currency}` : null,
    filters.budgetVersionId
      ? `${copy.filterVersion}: ${catalog.versions.find((item) => item.id === filters.budgetVersionId)?.name ?? filters.budgetVersionId}`
      : null,
    query ? `${copy.filterPeriodFrom}: ${query.period_from}` : null,
    query ? `${copy.filterPeriodTo}: ${query.period_to}` : null,
    filters.departmentId
      ? `${copy.filterDepartment}: ${catalog.departments.find((item) => item.id === filters.departmentId)?.code ?? filters.departmentId}`
      : null,
  ].filter((item): item is string => item !== null);

  const lastAnswer = [...messages].reverse().find((item) => item.answer)?.answer ?? null;

  function ask(text: string, category: string) {
    if (!userId || !organizationId || !query || !text.trim()) return;
    setBusy(true);
    setError(null);
    setMessages((current) => [
      ...current,
      { role: "user", text, status: "completed" },
      { role: "assistant", text: copy.copilotSending, status: "sending" },
    ]);
    const auth = sessionAuth(userId, organizationId);
    const conversationPromise = activeId
      ? Promise.resolve({ data: { id: activeId } })
      : createConversation(apiBaseUrl(), auth, { title: text.slice(0, 80), context });
    void conversationPromise
      .then(async (conversation) => {
        setActiveId(conversation.data.id);
        setMessages((current) =>
          current.map((item, index) =>
            index === current.length - 1 ? { ...item, status: "analyzing", text: copy.copilotAnalyzing } : item,
          ),
        );
        window.setTimeout(() => {
          setMessages((current) =>
            current.map((item, index) =>
              index === current.length - 1 ? { ...item, status: "querying", text: copy.copilotQuerying } : item,
            ),
          );
        }, 400);
        return sendConversationMessage(apiBaseUrl(), auth, conversation.data.id, {
          content: text,
          context,
        });
      })
      .then((result) => {
        setMessages((current) =>
          current.map((item, index) =>
            index === current.length - 1
              ? { role: "assistant", text: result.data.answer, status: "completed", answer: result.data }
              : item,
          ),
        );
        trackEvent("copilot_question_completed", { category });
        setQuestion("");
      })
      .catch((err: Error) => {
        setError(err);
        setMessages((current) =>
          current.map((item, index) =>
            index === current.length - 1
              ? { ...item, status: "failed", text: copy.copilotFailed }
              : item,
          ),
        );
      })
      .finally(() => setBusy(false));
  }

  const examples = [
    { label: copy.exampleVariance, text: copy.copilotExampleVariance, category: "variance" },
    { label: copy.exampleDrivers, text: copy.copilotExampleDrivers, category: "drivers" },
    { label: copy.exampleTrend, text: copy.copilotExampleTrend, category: "trend" },
  ];

  return (
    <CapabilityGate allowed={capabilities.can_use_copilot} hasSession={hasSession}>
      <PageHeader title={copy.copilotTitle} description={copy.copilotDescription} />
      <div className="mt-6 grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)_380px]">
        <aside className={`rounded-surface border border-border bg-surface p-4 ${listOpen ? "" : "hidden lg:block"}`}>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-secondary">{copy.conversationsTitle}</h2>
            <Button variant="ghost" onClick={() => setListOpen(false)} className="lg:hidden">
              {copy.collapseConversations}
            </Button>
          </div>
          <Button
            variant="secondary"
            className="mt-3 w-full"
            onClick={() => {
              setActiveId(null);
              setMessages([]);
            }}
          >
            {copy.newConversation}
          </Button>
          <ul className="mt-3 space-y-1">
            {conversations.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className="h-10 w-full truncate rounded-control px-2 text-left text-sm hover:bg-canvas"
                  onClick={() => setActiveId(item.id)}
                >
                  {item.title}
                </button>
              </li>
            ))}
          </ul>
        </aside>
        <section className="rounded-surface border border-border bg-surface p-6">
          <Button variant="ghost" className="lg:hidden" onClick={() => setListOpen(true)}>
            {copy.expandConversations}
          </Button>
          <h2 className="text-sm font-medium text-secondary">{copy.contextTitle}</h2>
          <ul className="mt-3 flex flex-wrap gap-2">
            {contextChips.map((chip) => (
              <li key={chip} className="rounded-pill bg-canvas px-3 py-1 text-xs text-primary">
                {chip}
              </li>
            ))}
          </ul>
          <div className="mt-4 flex flex-wrap gap-2">
            {examples.map((example) => (
              <Button
                key={example.category}
                variant="secondary"
                disabled={busy || !query}
                onClick={() => ask(example.text, example.category)}
              >
                {example.label}
              </Button>
            ))}
          </div>
          <div className="mt-6 max-w-[760px] space-y-3">
            {messages.map((item, index) => (
              <article key={index} className="rounded-control bg-canvas p-3 text-sm text-primary">
                <p>{item.text}</p>
                {item.answer ? (
                  <p className="mt-2 text-xs text-secondary">
                    {copy.copilotScopeUsed}: {item.answer.scope.period_from as string} –{" "}
                    {item.answer.scope.period_to as string}. {copy.copilotFiltersUsed}
                  </p>
                ) : null}
              </article>
            ))}
          </div>
          <label className="mt-6 flex flex-col gap-1 text-xs">
            <span className="font-medium text-secondary">{copy.askCopilot}</span>
            <textarea
              className="min-h-24 rounded-control border border-border px-3 py-2 text-sm"
              value={question}
              placeholder={copy.copilotPlaceholder}
              onChange={(event) => setQuestion(event.target.value)}
            />
          </label>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button disabled={!question.trim() || !query || busy} onClick={() => ask(question, "custom")}>
              {copy.askCopilot}
            </Button>
            <Button variant="ghost" onClick={() => setEvidenceOpen(true)}>
              {copy.viewEvidence}
            </Button>
            {messages.some((item) => item.status === "failed") ? (
              <Button variant="secondary" onClick={() => ask(question || copy.copilotExampleVariance, "retry")}>
                {copy.copilotRetry}
              </Button>
            ) : null}
          </div>
          {progress === "working" ? (
            <p className="mt-4 text-sm text-secondary" aria-live="polite">
              {copy.copilotAnalyzing}
            </p>
          ) : null}
          {progress === "long" ? (
            <p className="mt-4 text-sm text-secondary" aria-live="polite">
              {copy.copilotStillWorking}
            </p>
          ) : null}
          <ErrorBanner error={error} />
        </section>
        <aside className="hidden rounded-surface border border-border bg-surface p-4 lg:block">
          <EvidencePanel answer={lastAnswer} chips={contextChips} />
        </aside>
      </div>
      <Drawer open={evidenceOpen} title={copy.evidenceTitle} onClose={() => setEvidenceOpen(false)}>
        <EvidencePanel answer={lastAnswer} chips={contextChips} />
      </Drawer>
    </CapabilityGate>
  );
}

function EvidencePanel({
  answer,
  chips,
}: {
  answer: CopilotMessage | null;
  chips: string[];
}) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-primary">{copy.evidenceTitle}</h3>
      {!answer || answer.evidence.length === 0 ? (
        <p className="mt-2 text-sm text-secondary">{copy.copilotNoEvidence}</p>
      ) : (
        <ul className="mt-3 space-y-2 text-xs text-secondary">
          {answer.evidence.map((item, index) => (
            <li key={String(item.id ?? index)}>
              {String(item.tool ?? "")} · {String(item.label ?? "")}
            </li>
          ))}
        </ul>
      )}
      <ul className="mt-3 space-y-1 text-xs text-secondary">
        {chips.map((chip) => (
          <li key={chip}>{chip}</li>
        ))}
      </ul>
    </div>
  );
}
