"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { createOrganization, listImports, type ImportJob } from "@budgetlens/api-client";

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
import { downloadImportTemplate } from "@/lib/import-template";

export function ImportsPage() {
  const { userId, organizationId, selectedOrganization, capabilities, setOrganizationId } =
    useSession();
  const [form, setForm] = useState({
    name: "",
    slug: "",
    functional_currency: "MXN",
    fiscal_year_start_month: "1",
  });
  const [error, setError] = useState<Error | string | null>(null);
  const [jobs, setJobs] = useState<ImportJob[]>([]);
  const hasUser = Boolean(userId);
  const canImport = capabilities.can_import;
  const allowed = capabilities.can_view_technical_metrics
    ? false
    : organizationId
      ? canImport
      : hasUser;
  const auth = useMemo(() => sessionAuth(userId, organizationId), [organizationId, userId]);

  useEffect(() => {
    if (!userId || !organizationId) {
      setJobs([]);
      return;
    }
    void listImports(apiBaseUrl(), auth)
      .then((result) => setJobs(result.data.items))
      .catch((err: Error) => setError(err));
  }, [auth, organizationId, userId]);

  return (
    <CapabilityGate allowed={allowed} hasSession={hasUser} needsSession>
      <PageHeader
        eyebrow={copy.appName}
        title={copy.importsTitle}
        description={copy.importsDescription}
        actions={
          organizationId ? (
            <Link href="/imports/new">
              <Button>{copy.newImport}</Button>
            </Link>
          ) : null
        }
      />
      {!organizationId ? (
        <form
          className="mt-8 grid gap-3 rounded-surface border border-border bg-surface p-6 md:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (!userId) return;
            setError(null);
            void createOrganization(apiBaseUrl(), sessionAuth(userId), {
              name: form.name,
              slug: form.slug,
              functional_currency: form.functional_currency,
              fiscal_year_start_month: Number(form.fiscal_year_start_month),
            })
              .then((result) => setOrganizationId(result.data.id))
              .catch((err: Error) => setError(err));
          }}
        >
          <h2 className="text-lg font-semibold text-primary md:col-span-2">
            {copy.createOrganization}
          </h2>
          <Input
            required
            label={copy.name}
            value={form.name}
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
          />
          <Input
            required
            label={copy.slugLabel}
            value={form.slug}
            onChange={(event) => setForm((current) => ({ ...current, slug: event.target.value }))}
          />
          <Input
            required
            label={copy.currencyLabel}
            value={form.functional_currency}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                functional_currency: event.target.value.toUpperCase(),
              }))
            }
          />
          <Input
            required
            type="number"
            min={1}
            max={12}
            label={copy.fiscalStartLabel}
            value={form.fiscal_year_start_month}
            onChange={(event) =>
              setForm((current) => ({ ...current, fiscal_year_start_month: event.target.value }))
            }
          />
          <div className="md:col-span-2">
            <ErrorBanner error={error} />
          </div>
          <Button type="submit">{copy.createOrganization}</Button>
        </form>
      ) : (
        <section className="mt-8 space-y-6">
          <div className="rounded-surface border border-border bg-surface p-6">
            <p className="text-sm text-secondary">
              {selectedOrganization?.name} · {copy.currencyLabel}{" "}
              {selectedOrganization?.functional_currency}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="secondary" onClick={downloadImportTemplate}>
                {copy.downloadTemplate}
              </Button>
            </div>
            <p className="mt-3 text-sm text-secondary">{copy.templateHint}</p>
          </div>
          {jobs.length === 0 ? (
            <EmptyState
              title={copy.importListEmpty}
              detail={copy.emptyActuals}
              action={
                <Link className="text-sm font-medium text-brand-600" href="/imports/new">
                  {copy.newImport}
                </Link>
              }
            />
          ) : (
            <Table caption={copy.importsTitle}>
              <thead>
                <tr className="border-b border-border text-secondary">
                  <th className="py-2 font-medium">{copy.name}</th>
                  <th className="py-2 font-medium">{copy.status}</th>
                  <th className="py-2 font-medium">{copy.importType}</th>
                  <th className="py-2 font-medium">{copy.hashLabel}</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id} className="border-b border-border">
                    <td className="py-2">
                      <Link className="text-brand-600" href={`/imports/job/?id=${job.id}`}>
                        {job.original_filename}
                      </Link>
                    </td>
                    <td className="py-2">{job.status}</td>
                    <td className="py-2">{job.import_type}</td>
                    <td className="py-2">{job.sha256_short}</td>
                  </tr>
                ))}
              </tbody>
            </Table>
          )}
          <ErrorBanner error={error} />
        </section>
      )}
    </CapabilityGate>
  );
}
