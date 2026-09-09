"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { listScenarios, type Scenario } from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Table } from "@/components/ui/Table";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { EmptyState } from "@/components/layout/EmptyState";
import { PageHeader } from "@/components/layout/PageHeader";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";
import { baselineTypeLabel, scenarioStatusLabel } from "@/lib/labels";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";

export function ScenariosPage() {
  const { userId, organizationId, capabilities, generation } = useSession();
  const [items, setItems] = useState<Scenario[]>([]);
  const [error, setError] = useState<Error | string | null>(null);
  const hasSession = Boolean(userId && organizationId);

  useEffect(() => {
    if (!userId || !organizationId) {
      setItems([]);
      return;
    }
    void listScenarios(apiBaseUrl(), sessionAuth(userId, organizationId))
      .then((result) => {
        setItems(result.data.items);
        setError(null);
      })
      .catch((err: Error) => setError(err));
  }, [generation, organizationId, userId]);

  return (
    <CapabilityGate allowed={capabilities.can_create_scenario} hasSession={hasSession}>
      <PageHeader
        title={copy.scenariosTitle}
        description={copy.scenariosDescription}
        actions={
          <Link href="/scenarios/new">
            <Button>{copy.newScenario}</Button>
          </Link>
        }
      />
      <ErrorBanner error={error} />
      {items.length === 0 ? (
        <EmptyState
          title={copy.scenarioListEmpty}
          detail={copy.emptyScenarioImpact}
          action={
            <Link className="text-sm font-medium text-brand-600" href="/scenarios/new">
              {copy.newScenario}
            </Link>
          }
        />
      ) : (
        <Table className="mt-8" caption={copy.scenariosTitle}>
          <thead>
            <tr className="border-b border-border text-secondary">
              <th className="py-2 font-medium">{copy.name}</th>
              <th className="py-2 font-medium">{copy.baselineLabel}</th>
              <th className="py-2 font-medium">{copy.status}</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-b border-border">
                <td className="py-2">
                  <Link className="text-brand-600" href={`/scenarios/detail/?id=${item.id}`}>
                    {item.name}
                  </Link>
                </td>
                <td className="py-2">{baselineTypeLabel(item.baseline_type)}</td>
                <td className="py-2">{scenarioStatusLabel(item.status)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </CapabilityGate>
  );
}
