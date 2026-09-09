"use client";

import { useEffect, useState } from "react";
import {
  createConversation,
  deleteConversation,
  listConversationMessages,
  listConversations,
  sendConversationMessage,
  type Conversation,
  type ConversationTurn,
  type CopilotMessage,
} from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { Drawer } from "@/components/ui/Drawer";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Money } from "@/components/ui/Money";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { EmptyState } from "@/components/layout/EmptyState";
import { PageHeader } from "@/components/layout/PageHeader";
import { FilterBar } from "@/features/analysis/FilterBar";
import { useCatalogOptions } from "@/features/analysis/useCatalogOptions";
import { useAnalysisFilters } from "@/features/session/useAnalysisFilters";
import { useSession } from "@/features/session/SessionProvider";
import { trackEvent } from "@/lib/analytics";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";
import { queryFromFilters } from "@/lib/query-from-filters";

import {
  asEvidenceRecords,
  itemSummaries,
  metricPairs,
  scopeLines,
  type EvidenceRecordView,
} from "./evidence";

type ChatStatus = "sending" | "analyzing" | "querying" | "preparing" | "completed" | "failed";

type ChatItem = {
  id: string;
  role: "user" | "assistant";
  text: string;
  status: ChatStatus;
  answer?: CopilotMessage;
};

const STAGE_COPY: Record<Exclude<ChatStatus, "completed" | "failed">, string> = {
  sending: copy.copilotSending,
  analyzing: copy.copilotAnalyzing,
  querying: copy.copilotQuerying,
  preparing: copy.copilotPreparing,
};

export function CopilotPage() {
  const { userId, organizationId, selectedOrganization, capabilities, generation } = useSession();
  const catalog = useCatalogOptions();
  const { filters, update, reset } = useAnalysisFilters(catalog.versions);
  const [question, setQuestion] = useState("");
  const [lastQuestion, setLastQuestion] = useState("");
  const [askedScope, setAskedScope] = useState("");
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [error, setError] = useState<Error | string | null>(null);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [listOpen, setListOpen] = useState(true);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<"hidden" | "working" | "long">("hidden");
  const [pendingDelete, setPendingDelete] = useState<Conversation | null>(null);
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
  const scopeKey = query
    ? `${query.budget_version_id}:${query.period_from}:${query.period_to}:${query.department_id ?? ""}:${query.account_id ?? ""}`
    : "";

  useEffect(() => {
    setActiveId(null);
    setMessages([]);
    setError(null);
    setQuestion("");
    if (!userId || !organizationId) {
      setConversations([]);
      return;
    }
    void listConversations(apiBaseUrl(), sessionAuth(userId, organizationId))
      .then((result) => setConversations(result.data.items))
      .catch(() => setConversations([]));
  }, [generation, organizationId, userId]);

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
    filters.accountId
      ? `${copy.filterAccount}: ${catalog.accounts.find((item) => item.id === filters.accountId)?.code ?? filters.accountId}`
      : null,
  ].filter((item): item is string => item !== null);

  const lastAnswer = [...messages].reverse().find((item) => item.answer)?.answer ?? null;
  const contextChanged = Boolean(askedScope && scopeKey && askedScope !== scopeKey);

  function refreshConversations() {
    if (!userId || !organizationId) return;
    void listConversations(apiBaseUrl(), sessionAuth(userId, organizationId))
      .then((result) => setConversations(result.data.items))
      .catch(() => undefined);
  }

  function startNewConversation() {
    setActiveId(null);
    setMessages([]);
    setError(null);
  }

  function openConversation(id: string) {
    if (!userId || !organizationId) return;
    setActiveId(id);
    setError(null);
    void listConversationMessages(apiBaseUrl(), sessionAuth(userId, organizationId), id)
      .then((result) => setMessages(result.data.items.map(turnToChat)))
      .catch((err: Error) => {
        setError(err);
        setMessages([]);
      });
  }

  function ask(text: string, category: string) {
    if (!userId || !organizationId || !query || !text.trim()) return;
    setBusy(true);
    setError(null);
    setLastQuestion(text);
    setAskedScope(scopeKey);
    const pendingId = `pending-${Date.now()}`;
    setMessages((current) => [
      ...current,
      { id: `user-${pendingId}`, role: "user", text, status: "completed" },
      { id: pendingId, role: "assistant", text: copy.copilotSending, status: "sending" },
    ]);
    const auth = sessionAuth(userId, organizationId);
    const conversationPromise = activeId
      ? Promise.resolve({ data: { id: activeId } })
      : createConversation(apiBaseUrl(), auth, { title: text.slice(0, 80), context });
    const queryingTimer = window.setTimeout(() => patchPending(pendingId, "querying"), 400);
    const preparingTimer = window.setTimeout(() => patchPending(pendingId, "preparing"), 800);
    void conversationPromise
      .then(async (conversation) => {
        setActiveId(conversation.data.id);
        patchPending(pendingId, "analyzing");
        return sendConversationMessage(apiBaseUrl(), auth, conversation.data.id, {
          content: text,
          context,
        });
      })
      .then((result) => {
        setMessages((current) =>
          current.map((item) =>
            item.id === pendingId
              ? {
                  id: result.data.message_id,
                  role: "assistant",
                  text: result.data.answer,
                  status: "completed",
                  answer: result.data,
                }
              : item,
          ),
        );
        trackEvent("copilot_question_completed", { category });
        setQuestion("");
        refreshConversations();
      })
      .catch((err: Error) => {
        setError(err);
        setMessages((current) =>
          current.map((item) =>
            item.id === pendingId ? { ...item, status: "failed", text: copy.copilotFailed } : item,
          ),
        );
      })
      .finally(() => {
        window.clearTimeout(queryingTimer);
        window.clearTimeout(preparingTimer);
        setBusy(false);
      });
  }

  function patchPending(id: string, status: ChatStatus) {
    setMessages((current) =>
      current.map((item) =>
        item.id === id && item.status !== "completed" && item.status !== "failed"
          ? { ...item, status, text: STAGE_COPY[status as keyof typeof STAGE_COPY] ?? item.text }
          : item,
      ),
    );
  }

  function confirmDelete() {
    if (!userId || !organizationId || !pendingDelete) return;
    const target = pendingDelete;
    void deleteConversation(apiBaseUrl(), sessionAuth(userId, organizationId), target.id)
      .then(() => {
        setConversations((current) => current.filter((item) => item.id !== target.id));
        if (activeId === target.id) {
          startNewConversation();
        }
      })
      .catch((err: Error) => setError(err))
      .finally(() => setPendingDelete(null));
  }

  const examples = [
    { label: copy.exampleVariance, text: copy.copilotExampleVariance, category: "variance" },
    { label: copy.exampleDrivers, text: copy.copilotExampleDrivers, category: "drivers" },
    { label: copy.exampleTrend, text: copy.copilotExampleTrend, category: "trend" },
  ];

  return (
    <CapabilityGate allowed={capabilities.can_use_copilot} hasSession={hasSession}>
      <PageHeader title={copy.copilotTitle} description={copy.copilotDescription} />
      <FilterBar
        filters={filters}
        versions={catalog.versions}
        departments={catalog.departments}
        accounts={catalog.accounts}
        costCenters={catalog.costCenters}
        onChange={update}
        onReset={reset}
        showSort={false}
      />
      <div className="mt-6 grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)_380px]">
        <aside
          className={`rounded-surface border border-border bg-surface p-4 ${listOpen ? "" : "hidden lg:block"}`}
        >
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-sm font-medium text-secondary">{copy.conversationsTitle}</h2>
            <Button variant="ghost" onClick={() => setListOpen(false)} className="lg:hidden">
              {copy.collapseConversations}
            </Button>
          </div>
          <Button variant="secondary" className="mt-3 w-full" onClick={startNewConversation}>
            {copy.newConversation}
          </Button>
          {conversations.length === 0 ? (
            <p className="mt-3 text-sm text-secondary">{copy.noConversations}</p>
          ) : (
            <ul className="mt-3 space-y-1">
              {conversations.map((item) => (
                <li key={item.id} className="flex items-center gap-1">
                  <button
                    type="button"
                    aria-current={activeId === item.id ? "true" : undefined}
                    className={`h-10 min-w-0 flex-1 truncate rounded-control px-2 text-left text-sm hover:bg-canvas ${
                      activeId === item.id ? "bg-canvas font-medium" : ""
                    }`}
                    onClick={() => openConversation(item.id)}
                  >
                    {item.title}
                  </button>
                  <Button
                    variant="ghost"
                    className="shrink-0 px-2"
                    aria-label={`${copy.deleteConversation}: ${item.title}`}
                    onClick={() => setPendingDelete(item)}
                  >
                    <span aria-hidden="true">×</span>
                    <span className="sr-only">{copy.deleteConversation}</span>
                  </Button>
                </li>
              ))}
            </ul>
          )}
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
            {messages.length === 0 ? (
              <EmptyState title={copy.copilotEmptyTitle} detail={copy.copilotEmptyDetail} />
            ) : (
              messages.map((item) => (
                <article
                  key={item.id}
                  className="rounded-control bg-canvas p-3 text-sm text-primary"
                >
                  <p className="text-xs font-medium text-secondary">
                    {item.role === "user" ? copy.askCopilot : copy.copilotTitle}
                  </p>
                  <p className="mt-1">{item.text}</p>
                  {item.answer ? (
                    <p className="mt-2 text-xs text-secondary">
                      {copy.copilotScopeUsed}: {String(item.answer.scope.period_from ?? "")} –{" "}
                      {String(item.answer.scope.period_to ?? "")}. {copy.copilotFiltersUsed}
                    </p>
                  ) : null}
                  {item.answer?.limitations.length ? (
                    <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-secondary">
                      {item.answer.limitations.map((limitation) => (
                        <li key={limitation}>{limitation}</li>
                      ))}
                    </ul>
                  ) : null}
                </article>
              ))
            )}
          </div>
          {!query ? <p className="mt-6 text-sm text-secondary">{copy.copilotUnavailable}</p> : null}
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
            <Button
              disabled={!question.trim() || !query || busy}
              loading={busy}
              onClick={() => ask(question, "custom")}
            >
              {busy ? copy.copilotAnalyzing : copy.askCopilot}
            </Button>
            <Button variant="ghost" onClick={() => setEvidenceOpen(true)}>
              {copy.viewEvidence}
            </Button>
            {messages.some((item) => item.status === "failed") ? (
              <Button
                variant="secondary"
                disabled={busy || !query}
                onClick={() =>
                  ask(lastQuestion || question || copy.copilotExampleVariance, "retry")
                }
              >
                {copy.copilotRetry}
              </Button>
            ) : null}
          </div>
          {contextChanged ? (
            <p className="mt-3 text-sm text-secondary">{copy.copilotContextChanged}</p>
          ) : null}
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
          <ErrorBanner
            error={error}
            onRetry={
              lastQuestion
                ? () => ask(lastQuestion, "retry")
                : error
                  ? () => setError(null)
                  : undefined
            }
          />
        </section>
        <aside className="hidden rounded-surface border border-border bg-surface p-4 lg:block">
          <EvidencePanel answer={lastAnswer} chips={contextChips} />
        </aside>
      </div>
      <Drawer open={evidenceOpen} title={copy.evidenceTitle} onClose={() => setEvidenceOpen(false)}>
        <EvidencePanel answer={lastAnswer} chips={contextChips} />
      </Drawer>
      <Dialog
        open={pendingDelete !== null}
        title={copy.deleteConversation}
        onClose={() => setPendingDelete(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setPendingDelete(null)}>
              {copy.cancel}
            </Button>
            <Button variant="danger" onClick={confirmDelete}>
              {copy.deleteConversation}
            </Button>
          </>
        }
      >
        <p className="text-sm text-secondary">{copy.confirmDeleteConversation}</p>
      </Dialog>
    </CapabilityGate>
  );
}

function turnToChat(item: ConversationTurn): ChatItem {
  return {
    id: item.id,
    role: item.role,
    text: item.content,
    status: "completed",
  };
}

function EvidencePanel({ answer, chips }: { answer: CopilotMessage | null; chips: string[] }) {
  const records = answer ? asEvidenceRecords(answer.evidence) : [];
  return (
    <div>
      <h3 className="text-sm font-semibold text-primary">{copy.evidenceTitle}</h3>
      {records.length === 0 ? (
        <p className="mt-2 text-sm text-secondary">{copy.copilotNoEvidence}</p>
      ) : (
        <ul className="mt-3 space-y-4">
          {records.map((item) => (
            <li key={item.id} className="rounded-control border border-border p-3">
              <EvidenceCard record={item} />
            </li>
          ))}
        </ul>
      )}
      {answer ? (
        <ul className="mt-4 space-y-1 text-xs text-secondary">
          {scopeLines(answer.scope).map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : null}
      {answer?.limitations.length ? (
        <div className="mt-4">
          <h4 className="text-xs font-medium text-secondary">{copy.copilotLimitations}</h4>
          <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-secondary">
            {answer.limitations.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
      ) : null}
      <ul className="mt-3 space-y-1 text-xs text-secondary">
        {chips.map((chip) => (
          <li key={chip}>{chip}</li>
        ))}
      </ul>
    </div>
  );
}

function EvidenceCard({ record }: { record: EvidenceRecordView }) {
  const metrics = metricPairs(record.data);
  const items = itemSummaries(record.data);
  const currency = typeof record.data.currency === "string" ? record.data.currency : "";
  const scoped = record.data.scope;
  const scopeCurrency =
    scoped && typeof scoped === "object" && scoped !== null && "currency" in scoped
      ? String((scoped as { currency?: string }).currency ?? currency)
      : currency;
  return (
    <div>
      <p className="text-sm font-medium text-primary">
        {record.label || record.tool} · {record.id}
      </p>
      <p className="mt-1 text-xs text-secondary">
        {copy.evidenceTool}: {record.tool}
      </p>
      {metrics.length ? (
        <dl className="mt-2 space-y-1 text-xs text-secondary">
          {metrics.map((item) => (
            <div key={item.label} className="flex justify-between gap-3">
              <dt>{item.label}</dt>
              <dd className="tabular-nums text-primary">
                {item.money && scopeCurrency ? (
                  <Money value={item.value} currency={scopeCurrency} />
                ) : (
                  item.value
                )}
              </dd>
            </div>
          ))}
        </dl>
      ) : null}
      {items.length ? (
        <div className="mt-3">
          <p className="text-xs font-medium text-secondary">{copy.evidenceAggregates}</p>
          <ul className="mt-1 space-y-1 text-xs text-secondary">
            {items.map((item) => (
              <li key={item.name} className="flex justify-between gap-3">
                <span>{item.name}</span>
                {item.variance && scopeCurrency ? (
                  <Money value={item.variance} currency={scopeCurrency} />
                ) : (
                  <span>{item.variance}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
