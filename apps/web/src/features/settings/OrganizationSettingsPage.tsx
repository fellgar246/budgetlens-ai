"use client";

import { useEffect, useState } from "react";
import { patchOrganization } from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { PageHeader } from "@/components/layout/PageHeader";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";

export function OrganizationSettingsPage() {
  const { userId, organizationId, selectedOrganization, capabilities } = useSession();
  const [name, setName] = useState("");
  const [fiscalMonth, setFiscalMonth] = useState("1");
  const [message, setMessage] = useState<string | null>(null);
  const hasSession = Boolean(userId && organizationId);

  useEffect(() => {
    if (!selectedOrganization) {
      return;
    }
    setName(selectedOrganization.name);
    setFiscalMonth(String(selectedOrganization.fiscal_year_start_month));
  }, [selectedOrganization]);

  return (
    <CapabilityGate
      allowed={capabilities.can_view_dashboard || capabilities.can_manage_organization}
      hasSession={hasSession}
    >
      <PageHeader title={copy.settingsTitle} description={copy.settingsDescription} />
      <form
        className="mt-8 grid max-w-xl gap-3 rounded-surface border border-border bg-surface p-6"
        onSubmit={(event) => {
          event.preventDefault();
          if (!userId || !organizationId || !selectedOrganization) {
            return;
          }
          setMessage(null);
          void patchOrganization(apiBaseUrl(), { token: userId, organizationId }, organizationId, {
            version: selectedOrganization.version,
            name,
            fiscal_year_start_month: Number(fiscalMonth),
          })
            .then(() => {
              window.dispatchEvent(new Event("budgetlens-session"));
              setMessage(copy.saveOrganization);
            })
            .catch((error: Error) => setMessage(error.message));
        }}
      >
        <label className="flex flex-col gap-1 text-xs">
          <span className="font-medium text-secondary">{copy.name}</span>
          <input
            className="h-10 rounded-control border border-border px-3 text-sm"
            value={name}
            disabled={!capabilities.can_manage_organization}
            onChange={(event) => setName(event.target.value)}
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span className="font-medium text-secondary">{copy.currencyLabel}</span>
          <input
            className="h-10 rounded-control border border-border bg-canvas px-3 text-sm"
            value={selectedOrganization?.functional_currency ?? ""}
            disabled
          />
        </label>
        <label className="flex flex-col gap-1 text-xs">
          <span className="font-medium text-secondary">{copy.fiscalStartLabel}</span>
          <input
            type="number"
            min={1}
            max={12}
            className="h-10 rounded-control border border-border px-3 text-sm"
            value={fiscalMonth}
            disabled={!capabilities.can_manage_organization}
            onChange={(event) => setFiscalMonth(event.target.value)}
          />
        </label>
        {capabilities.can_manage_organization ? (
          <Button type="submit">{copy.saveOrganization}</Button>
        ) : null}
        {message ? <p className="text-sm text-secondary">{message}</p> : null}
      </form>
    </CapabilityGate>
  );
}
