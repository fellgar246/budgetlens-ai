"use client";

import { useMemo, useState } from "react";
import {
  cancelImport,
  commitImport,
  createImportJob,
  createOrganization,
  downloadAuthorized,
  importErrorReportUrl,
  listImportErrors,
  previewImport,
  sha256Hex,
  uploadImportContent,
  validateImport,
  type ImportErrorItem,
  type ImportJob,
  type ImportPreview,
} from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { EmptyState } from "@/components/layout/EmptyState";
import { PageHeader } from "@/components/layout/PageHeader";
import { useCatalogOptions } from "@/features/analysis/useCatalogOptions";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { downloadImportTemplate } from "@/lib/import-template";

const CANONICAL = [
  "period",
  "account_code",
  "department_code",
  "cost_center_code",
  "amount",
  "currency",
] as const;

export function ImportsPage() {
  const { userId, organizationId, selectedOrganization, capabilities, setOrganizationId } =
    useSession();
  const catalog = useCatalogOptions();
  const [form, setForm] = useState({
    name: "",
    slug: "",
    functional_currency: "MXN",
    fiscal_year_start_month: "1",
  });
  const [error, setError] = useState<string | null>(null);
  const [importType, setImportType] = useState<"budget" | "actual">("actual");
  const [versionId, setVersionId] = useState("");
  const [job, setJob] = useState<ImportJob | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [errors, setErrors] = useState<ImportErrorItem[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const hasUser = Boolean(userId);
  const canImport = capabilities.can_import;
  const commitEnabled = job?.status === "ready" && job.error_count === 0 && canImport;
  const allowed = capabilities.can_view_technical_metrics
    ? false
    : organizationId
      ? canImport
      : hasUser;
  const auth = useMemo(() => ({ token: userId, organizationId }), [organizationId, userId]);
  const draftVersions = catalog.versions.filter((item) => item.status === "draft");

  return (
    <CapabilityGate allowed={allowed} hasSession={hasUser} needsSession>
      <PageHeader
        eyebrow={copy.appName}
        title={copy.importsTitle}
        description={copy.importsDescription}
      />

      {!organizationId ? (
        <form
          className="mt-8 grid gap-3 rounded-surface border border-border bg-surface p-6 md:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault();
            if (!userId) return;
            setError(null);
            void createOrganization(
              apiBaseUrl(),
              { token: userId },
              {
                name: form.name,
                slug: form.slug,
                functional_currency: form.functional_currency,
                fiscal_year_start_month: Number(form.fiscal_year_start_month),
              },
            )
              .then((result) => setOrganizationId(result.data.id))
              .catch((err: Error) => setError(err.message));
          }}
        >
          <h2 className="md:col-span-2 text-lg font-semibold text-primary">
            {copy.createOrganization}
          </h2>
          <input
            required
            className="h-10 rounded-control border border-border px-3 text-sm"
            placeholder={copy.name}
            value={form.name}
            onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
          />
          <input
            required
            className="h-10 rounded-control border border-border px-3 text-sm"
            placeholder={copy.slugLabel}
            value={form.slug}
            onChange={(event) => setForm((current) => ({ ...current, slug: event.target.value }))}
          />
          <input
            required
            className="h-10 rounded-control border border-border px-3 text-sm"
            placeholder={copy.currencyLabel}
            value={form.functional_currency}
            onChange={(event) =>
              setForm((current) => ({
                ...current,
                functional_currency: event.target.value.toUpperCase(),
              }))
            }
          />
          <input
            required
            type="number"
            min={1}
            max={12}
            className="h-10 rounded-control border border-border px-3 text-sm"
            placeholder={copy.fiscalStartLabel}
            value={form.fiscal_year_start_month}
            onChange={(event) =>
              setForm((current) => ({ ...current, fiscal_year_start_month: event.target.value }))
            }
          />
          {error ? <p className="md:col-span-2 text-sm text-danger">{error}</p> : null}
          <Button type="submit">{copy.createOrganization}</Button>
        </form>
      ) : (
        <section className="mt-8 space-y-6">
          <div className="rounded-surface border border-border bg-surface p-6">
            <p className="text-sm text-secondary">
              {selectedOrganization?.name} · {copy.currencyLabel}{" "}
              {selectedOrganization?.functional_currency} · {copy.fiscalStartLabel}{" "}
              {selectedOrganization?.fiscal_year_start_month}
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              <Button variant="secondary" onClick={downloadImportTemplate}>
                {copy.downloadTemplate}
              </Button>
            </div>
            <p className="mt-3 text-sm text-secondary">{copy.templateHint}</p>
          </div>
          <div className="rounded-surface border border-border bg-surface p-6">
            <h2 className="text-lg font-semibold text-primary">{copy.uploadFile}</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <label className="flex flex-col gap-1 text-xs">
                <span className="font-medium text-secondary">{copy.importType}</span>
                <select
                  className="h-10 rounded-control border border-border px-3 text-sm"
                  value={importType}
                  onChange={(event) => setImportType(event.target.value as "budget" | "actual")}
                >
                  <option value="actual">{copy.importActual}</option>
                  <option value="budget">{copy.importBudget}</option>
                </select>
              </label>
              {importType === "budget" ? (
                <label className="flex flex-col gap-1 text-xs">
                  <span className="font-medium text-secondary">{copy.filterVersion}</span>
                  <select
                    className="h-10 rounded-control border border-border px-3 text-sm"
                    value={versionId}
                    onChange={(event) => setVersionId(event.target.value)}
                  >
                    <option value="">{copy.chooseVersion}</option>
                    {draftVersions.map((version) => (
                      <option key={version.id} value={version.id}>
                        {version.name} · {version.fiscal_year}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
            </div>
            <input
              className="mt-4 block text-sm"
              type="file"
              accept=".csv,.xlsx"
              disabled={!canImport || busy || (importType === "budget" && !versionId)}
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (!file || !userId || !organizationId) return;
                setBusy(true);
                setError(null);
                void file
                  .arrayBuffer()
                  .then(async (buffer) => {
                    const digest = await sha256Hex(buffer);
                    const created = await createImportJob(apiBaseUrl(), auth, {
                      import_type: importType,
                      budget_version_id: importType === "budget" ? versionId : null,
                      original_filename: file.name,
                      size_bytes: file.size,
                      sha256: digest,
                    });
                    await uploadImportContent(
                      apiBaseUrl(),
                      auth,
                      created.data.id,
                      file,
                      file.type || "application/octet-stream",
                    );
                    const nextPreview = await previewImport(apiBaseUrl(), auth, created.data.id);
                    setJob(created.data);
                    setPreview(nextPreview.data);
                    setMapping(nextPreview.data.proposed_mapping);
                  })
                  .catch((err: Error) => setError(err.message))
                  .finally(() => setBusy(false));
              }}
            />
            <p className="mt-3 text-sm text-secondary">{copy.chooseFile}</p>
          </div>
          {preview ? (
            <div className="rounded-surface border border-border bg-surface p-6">
              <h2 className="text-lg font-semibold text-primary">{copy.mapColumns}</h2>
              <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                {CANONICAL.map((field) => (
                  <label key={field} className="flex flex-col gap-1 text-xs">
                    <span className="font-medium text-secondary">{field}</span>
                    <select
                      className="h-10 rounded-control border border-border px-3 text-sm"
                      value={mapping[field] ?? ""}
                      onChange={(event) =>
                        setMapping((current) => ({ ...current, [field]: event.target.value }))
                      }
                    >
                      <option value="">—</option>
                      {preview.headers.map((header) => (
                        <option key={header} value={header}>
                          {header}
                        </option>
                      ))}
                    </select>
                  </label>
                ))}
              </div>
              <div className="mt-4">
                <Button
                  disabled={busy}
                  onClick={() => {
                    if (!job) return;
                    setBusy(true);
                    void validateImport(apiBaseUrl(), auth, job.id, {
                      mapping,
                      create_missing_dimensions: false,
                    })
                      .then(async (result) => {
                        setJob(result.data);
                        const [nextPreview, nextErrors] = await Promise.all([
                          previewImport(apiBaseUrl(), auth, job.id),
                          listImportErrors(apiBaseUrl(), auth, job.id),
                        ]);
                        setPreview(nextPreview.data);
                        setErrors(nextErrors.data.items);
                      })
                      .catch((err: Error) => setError(err.message))
                      .finally(() => setBusy(false));
                  }}
                >
                  {copy.previewTitle}
                </Button>
              </div>
            </div>
          ) : (
            <EmptyState title={copy.previewTitle} detail={copy.previewEmpty} />
          )}
          {job && preview && job.status !== "created" ? (
            <div className="rounded-surface border border-border bg-surface p-6">
              <p className="text-sm text-secondary">
                {job.original_filename} · {job.valid_count}/{job.row_count} ·{" "}
                {job.valid_amount_total} {selectedOrganization?.functional_currency}
              </p>
              {job.status === "ready" ? (
                <p className="mt-2 text-sm text-success">{copy.importReady}</p>
              ) : null}
              {job.status === "invalid" ? (
                <p className="mt-2 text-sm text-danger">{copy.importInvalid}</p>
              ) : null}
              {job.status === "applied" ? (
                <p className="mt-2 text-sm text-success">{copy.importApplied}</p>
              ) : null}
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr className="text-left text-secondary">
                      {["period", "account_code", "department_code", "amount", "currency"].map(
                        (header) => (
                          <th key={header} className="pb-2 pr-4 font-medium">
                            {header}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.items.map((row) => (
                      <tr key={row.row_number} className="border-t border-border">
                        <td className="py-2 pr-4">{row.period}</td>
                        <td className="py-2 pr-4">{row.account_code}</td>
                        <td className="py-2 pr-4">{row.department_code}</td>
                        <td className="py-2 pr-4 font-variant-numeric">{row.amount}</td>
                        <td className="py-2 pr-4">{row.currency}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {errors.length > 0 ? (
                <ul className="mt-4 space-y-1 text-sm text-danger">
                  {errors.map((item) => (
                    <li key={`${item.row_number}-${item.field}-${item.code}`}>
                      Fila {item.row_number}: {item.code} · {item.message}
                    </li>
                  ))}
                </ul>
              ) : null}
            </div>
          ) : null}
          {error ? <p className="text-sm text-danger">{error}</p> : null}
          <div className="flex flex-wrap gap-2">
            <Button
              disabled={!commitEnabled || busy}
              title={commitEnabled ? copy.commitImport : copy.commitBlocked}
              onClick={() => {
                if (!job) return;
                setBusy(true);
                void commitImport(apiBaseUrl(), auth, job.id)
                  .then((result) => setJob(result.data))
                  .catch((err: Error) => setError(err.message))
                  .finally(() => setBusy(false));
              }}
            >
              {copy.commitImport}
            </Button>
            <Button
              variant="secondary"
              disabled={!job || job.error_count === 0}
              onClick={() => {
                if (!job) return;
                void downloadAuthorized(
                  importErrorReportUrl(apiBaseUrl(), job.id),
                  auth,
                  `budgetlens-import-errors-${job.id}.csv`,
                );
              }}
            >
              {copy.downloadErrors}
            </Button>
            <Button
              variant="ghost"
              disabled={!job || job.status === "applied" || busy}
              onClick={() => {
                if (!job) return;
                void cancelImport(apiBaseUrl(), auth, job.id).then((result) => setJob(result.data));
              }}
            >
              {copy.cancelImport}
            </Button>
          </div>
        </section>
      )}
    </CapabilityGate>
  );
}
