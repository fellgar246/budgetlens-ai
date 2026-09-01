"use client";

import { useEffect, useState } from "react";
import { listAuditEvents, type AuditEvent } from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Input } from "@/components/ui/Input";
import { Table } from "@/components/ui/Table";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { EmptyState } from "@/components/layout/EmptyState";
import { PageHeader } from "@/components/layout/PageHeader";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";

export function AuditPage() {
  const { userId, organizationId, capabilities } = useSession();
  const [items, setItems] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<Error | string | null>(null);
  const [action, setAction] = useState("");
  const [actor, setActor] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const hasSession = Boolean(userId && organizationId);

  function load() {
    if (!userId || !organizationId) return;
    void listAuditEvents(apiBaseUrl(), sessionAuth(userId, organizationId), {
      action: action || undefined,
      actor_id: actor || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
      .then((result) => {
        setItems(result.data.items);
        setError(null);
      })
      .catch((err: Error) => setError(err));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [organizationId, userId]);

  return (
    <CapabilityGate allowed={capabilities.can_manage_members} hasSession={hasSession}>
      <PageHeader title={copy.auditTitle} description={copy.auditDescription} />
      <div className="mt-6 grid gap-3 md:grid-cols-4">
        <Input
          label={copy.filterActor}
          value={actor}
          onChange={(event) => setActor(event.target.value)}
        />
        <Input
          label={copy.filterAction}
          value={action}
          onChange={(event) => setAction(event.target.value)}
        />
        <Input
          type="date"
          label={copy.filterDateFrom}
          value={dateFrom}
          onChange={(event) => setDateFrom(event.target.value)}
        />
        <Input
          type="date"
          label={copy.filterDateTo}
          value={dateTo}
          onChange={(event) => setDateTo(event.target.value)}
        />
      </div>
      <Button className="mt-3" variant="secondary" onClick={load}>
        {copy.applyFilters}
      </Button>
      <ErrorBanner error={error} />
      {items.length === 0 ? (
        <EmptyState title={copy.auditEmpty} detail={copy.auditDescription} />
      ) : (
        <Table className="mt-6" caption={copy.auditTitle}>
          <thead>
            <tr className="border-b border-border text-secondary">
              <th className="py-2 font-medium">{copy.filterAction}</th>
              <th className="py-2 font-medium">{copy.filterActor}</th>
              <th className="py-2 font-medium">{copy.resourceType}</th>
              <th className="py-2 font-medium">{copy.outcome}</th>
              <th className="py-2 font-medium">{copy.traceLabel}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.event_id} className="border-b border-border">
                <td className="py-2">{item.action}</td>
                <td className="py-2">
                  {item.actor.type}/{item.actor.id}
                </td>
                <td className="py-2">{item.resource.type}</td>
                <td className="py-2">{item.outcome}</td>
                <td className="py-2">{item.trace_id}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </CapabilityGate>
  );
}
