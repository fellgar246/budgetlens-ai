"use client";

import { useEffect, useState } from "react";
import { patchOrganization } from "@budgetlens/api-client";

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Input } from "@/components/ui/Input";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { PageHeader } from "@/components/layout/PageHeader";
import { useToast } from "@/components/ui/Toast";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";

export function OrganizationSettingsPage() {
  const { userId, organizationId, selectedOrganization, capabilities } = useSession();
  const toast = useToast();
  const [name, setName] = useState("");
  const [fiscalMonth, setFiscalMonth] = useState("1");
  const [retentionDays, setRetentionDays] = useState("90");
  const [message, setMessage] = useState<string | Error | null>(null);
  const hasSession = Boolean(userId && organizationId);
  const fiscalChanged =
    selectedOrganization && Number(fiscalMonth) !== selectedOrganization.fiscal_year_start_month;

  useEffect(() => {
    if (!selectedOrganization) {
      return;
    }
    setName(selectedOrganization.name);
    setFiscalMonth(String(selectedOrganization.fiscal_year_start_month));
    setRetentionDays(String(selectedOrganization.conversation_retention_days ?? 90));
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
          void patchOrganization(
            apiBaseUrl(),
            sessionAuth(userId, organizationId),
            organizationId,
            {
              version: selectedOrganization.version,
              name,
              fiscal_year_start_month: Number(fiscalMonth),
              conversation_retention_days: Number(retentionDays),
            },
          )
            .then(() => {
              window.dispatchEvent(new Event("budgetlens-session"));
              toast.push(copy.toastSaved);
              setMessage(copy.saveOrganization);
            })
            .catch((error: Error) => setMessage(error));
        }}
      >
        <Input
          label={copy.name}
          value={name}
          disabled={!capabilities.can_manage_organization}
          onChange={(event) => setName(event.target.value)}
        />
        <Input
          label={copy.currencyLabel}
          value={selectedOrganization?.functional_currency ?? ""}
          disabled
          hint={copy.currencyLocked}
        />
        <Input
          type="number"
          min={1}
          max={12}
          label={copy.fiscalStartLabel}
          value={fiscalMonth}
          disabled={!capabilities.can_manage_organization}
          onChange={(event) => setFiscalMonth(event.target.value)}
        />
        {fiscalChanged ? <Alert title={copy.fiscalWarning} tone="warning" /> : null}
        <Input
          type="number"
          min={7}
          max={365}
          label={copy.conversationRetentionLabel}
          value={retentionDays}
          disabled={!capabilities.can_manage_organization}
          onChange={(event) => setRetentionDays(event.target.value)}
        />
        {capabilities.can_manage_organization ? (
          <Button type="submit">{copy.saveOrganization}</Button>
        ) : null}
        {message && message !== copy.saveOrganization ? <ErrorBanner error={message} /> : null}
        {message === copy.saveOrganization ? <p className="text-sm text-secondary">{message}</p> : null}
      </form>
    </CapabilityGate>
  );
}
