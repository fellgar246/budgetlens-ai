"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import {
  cancelImport,
  commitImport,
  createImportJob,
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

import { Alert } from "@/components/ui/Alert";
import { Button } from "@/components/ui/Button";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Select } from "@/components/ui/Select";
import { Table } from "@/components/ui/Table";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { PageHeader } from "@/components/layout/PageHeader";
import { useCatalogOptions } from "@/features/analysis/useCatalogOptions";
import { useSession } from "@/features/session/SessionProvider";
import { trackEvent } from "@/lib/analytics";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";

const MAX_BYTES = 25 * 1024 * 1024;
const CANONICAL = [
  "period",
  "account_code",
  "account_name",
  "account_type",
  "department_code",
  "department_name",
  "cost_center_code",
  "cost_center_name",
  "amount",
  "currency",
  "source_reference",
] as const;
const REQUIRED = new Set(["period", "account_code", "department_code", "amount", "currency"]);
const STEPS = [
  copy.importStepType,
  copy.importStepMapping,
  copy.importStepValidation,
  copy.importStepConfirm,
  copy.importStepResult,
];

export function ImportWizardPage() {
  const { userId, organizationId, selectedOrganization, capabilities } = useSession();
  const catalog = useCatalogOptions();
  const [step, setStep] = useState(1);
  const [importType, setImportType] = useState<"budget" | "actual">("actual");
  const [versionId, setVersionId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<ImportJob | null>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [errors, setErrors] = useState<ImportErrorItem[]>([]);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [delimiter, setDelimiter] = useState<"," | ";" | "\t" | "">("");
  const [sheetName, setSheetName] = useState("");
  const [amountLocale, setAmountLocale] = useState<"en" | "es">("es");
  const [createMissing, setCreateMissing] = useState(false);
  const [understood, setUnderstood] = useState(false);
  const [busy, setBusy] = useState(false);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<Error | string | null>(null);
  const hasSession = Boolean(userId && organizationId);
  const auth = useMemo(() => sessionAuth(userId, organizationId), [organizationId, userId]);
  const draftVersions = catalog.versions.filter((item) => item.status === "draft");
  const replaces = (preview?.replaced_records ?? 0) > 0;
  const commitEnabled = job?.status === "ready" && job.error_count === 0 && (!replaces || understood);

  useEffect(() => {
    if (!busy) {
      setWorking(false);
      return;
    }
    const timer = window.setTimeout(() => setWorking(true), 1000);
    return () => window.clearTimeout(timer);
  }, [busy]);

  async function uploadSelected(nextFile: File, keepMapping = true) {
    if (!userId || !organizationId) return;
    if (nextFile.size > MAX_BYTES) {
      setError(copy.importLimits);
      return;
    }
    setBusy(true);
    setError(null);
    const previousMapping = keepMapping ? mapping : {};
    try {
      const digest = await sha256Hex(await nextFile.arrayBuffer());
      const created = await createImportJob(apiBaseUrl(), auth, {
        import_type: importType,
        budget_version_id: importType === "budget" ? versionId : null,
        original_filename: nextFile.name,
        size_bytes: nextFile.size,
        sha256: digest,
      });
      await uploadImportContent(
        apiBaseUrl(),
        auth,
        created.data.id,
        nextFile,
        nextFile.type || "application/octet-stream",
      );
      const nextPreview = await previewImport(apiBaseUrl(), auth, created.data.id);
      setFile(nextFile);
      setJob(created.data);
      setPreview(nextPreview.data);
      setMapping(
        Object.keys(previousMapping).length ? previousMapping : nextPreview.data.proposed_mapping,
      );
      setDelimiter((nextPreview.data.delimiter as "," | ";" | "\t" | "") || "");
      setSheetName(nextPreview.data.job.sheet_name ?? nextPreview.data.available_sheets[0] ?? "");
      trackEvent("import_started", { import_type: importType });
      setStep(2);
    } catch (err) {
      setError(err as Error);
    } finally {
      setBusy(false);
    }
  }

  return (
    <CapabilityGate allowed={capabilities.can_import} hasSession={hasSession}>
      <PageHeader title={copy.importWizardTitle} description={copy.importsDescription} />
      <ol className="mt-6 flex flex-wrap gap-3 text-sm" aria-label={copy.wizardStep}>
        {STEPS.map((label, index) => (
          <li
            key={label}
            className={index + 1 === step ? "font-semibold text-brand-700" : "text-secondary"}
          >
            {index + 1}. {label}
          </li>
        ))}
      </ol>
      <p className="mt-2 text-xs text-secondary lg:hidden">{copy.tabletHint}</p>
      {working ? (
        <p className="mt-4 text-sm text-secondary" aria-live="polite">
          {copy.importWorking}
        </p>
      ) : null}
      <ErrorBanner error={error} />

      {step === 1 ? (
        <section className="mt-6 space-y-4 rounded-surface border border-border bg-surface p-6">
          <div className="grid gap-3 md:grid-cols-2">
            <Select
              label={copy.importType}
              value={importType}
              onChange={(event) => setImportType(event.target.value as "budget" | "actual")}
            >
              <option value="actual">{copy.importActual}</option>
              <option value="budget">{copy.importBudget}</option>
            </Select>
            {importType === "budget" ? (
              <Select
                label={copy.filterVersion}
                value={versionId}
                onChange={(event) => setVersionId(event.target.value)}
              >
                <option value="">{copy.chooseVersion}</option>
                {draftVersions.map((version) => (
                  <option key={version.id} value={version.id}>
                    {version.name} · {version.fiscal_year}
                  </option>
                ))}
              </Select>
            ) : null}
          </div>
          <label
            className="flex min-h-32 cursor-pointer flex-col items-center justify-center rounded-surface border border-dashed border-border bg-canvas px-4 py-8 text-center"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              const next = event.dataTransfer.files[0];
              if (next) void uploadSelected(next, false);
            }}
          >
            <span className="text-sm font-medium text-primary">{copy.dropzoneLabel}</span>
            <span className="mt-2 text-xs text-secondary">{copy.importLimits}</span>
            <input
              className="sr-only"
              type="file"
              accept=".csv,.xlsx"
              disabled={busy || (importType === "budget" && !versionId)}
              onChange={(event) => {
                const next = event.target.files?.[0];
                if (next) void uploadSelected(next, false);
              }}
            />
          </label>
        </section>
      ) : null}

      {step === 2 && preview ? (
        <section className="mt-6 space-y-4 rounded-surface border border-border bg-surface p-6">
          <p className="text-sm text-secondary">{copy.mappingHint}</p>
          {file ? (
            <p className="text-sm text-primary">
              {copy.fileSelected}: {file.name} · {copy.fileSize} {file.size} B
            </p>
          ) : null}
          <Button variant="secondary" onClick={() => document.getElementById("replace-file")?.click()}>
            {copy.replaceFile}
          </Button>
          <input
            id="replace-file"
            className="sr-only"
            type="file"
            accept=".csv,.xlsx"
            onChange={(event) => {
              const next = event.target.files?.[0];
              if (next) void uploadSelected(next, true);
            }}
          />
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {CANONICAL.map((field) => (
              <Select
                key={field}
                label={`${field} · ${REQUIRED.has(field) ? copy.requiredField : copy.optionalField}`}
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
              </Select>
            ))}
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {preview.available_sheets.length > 1 ? (
              <Select
                label={copy.sheetLabel}
                value={sheetName}
                onChange={(event) => setSheetName(event.target.value)}
              >
                {preview.available_sheets.map((sheet) => (
                  <option key={sheet} value={sheet}>
                    {sheet}
                  </option>
                ))}
              </Select>
            ) : null}
            {preview.delimiter ? (
              <Select
                label={copy.confirmDelimiter}
                value={delimiter}
                onChange={(event) => setDelimiter(event.target.value as "," | ";" | "\t")}
              >
                <option value=",">{copy.delimiterComma}</option>
                <option value=";">{copy.delimiterSemicolon}</option>
                <option value={"\t"}>{copy.delimiterTab}</option>
              </Select>
            ) : null}
            <Select
              label={copy.decimalLocale}
              value={amountLocale}
              onChange={(event) => setAmountLocale(event.target.value as "en" | "es")}
            >
              <option value="es">{copy.localeEs}</option>
              <option value="en">{copy.localeEn}</option>
            </Select>
          </div>
          {preview.delimiter_ambiguous ? <Alert title={copy.delimiterAmbiguous} tone="warning" /> : null}
          <Table caption={copy.sampleRows}>
            <thead>
              <tr className="text-left text-secondary">
                {preview.headers.slice(0, 5).map((header) => (
                  <th key={header} className="pb-2 pr-4 font-medium">
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.items.slice(0, 5).map((row, index) => (
                <tr key={index} className="border-t border-border">
                  {preview.headers.slice(0, 5).map((header) => (
                    <td key={header} className="py-2 pr-4">
                      {row[header] ?? row[header.toLowerCase()] ?? ""}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </Table>
        </section>
      ) : null}

      {step === 3 && job && preview ? (
        <section className="mt-6 space-y-4 rounded-surface border border-border bg-surface p-6">
          <div className="grid gap-3 md:grid-cols-4">
            <Stat label={copy.periodLabel} value={`${job.valid_count + job.error_count}`} />
            <Stat label={copy.validRows} value={String(job.valid_count)} />
            <Stat label={copy.warningRows} value={String(job.warning_count)} />
            <Stat label={copy.errorRows} value={String(job.error_count)} />
          </div>
          <p className="text-sm text-secondary">
            {copy.periodRange}: {job.period_min}–{job.period_max} · {job.valid_amount_total}{" "}
            {selectedOrganization?.functional_currency}
          </p>
          {preview.error_groups.length > 0 ? (
            <ul className="space-y-1 text-sm text-danger">
              {preview.error_groups.map((group) => (
                <li key={`${group.code}-${group.severity}`}>
                  {group.code} · {group.count} · {group.sample_message}
                </li>
              ))}
            </ul>
          ) : null}
          {errors.length > 0 ? (
            <ul className="space-y-1 text-sm text-danger">
              {errors.slice(0, 8).map((item) => (
                <li key={`${item.row_number}-${item.field}-${item.code}`}>
                  Fila {item.row_number}: {item.code} · {item.message}
                </li>
              ))}
            </ul>
          ) : null}
        </section>
      ) : null}

      {step === 4 && job && preview ? (
        <section className="mt-6 space-y-4 rounded-surface border border-border bg-surface p-6">
          <Alert title={copy.importImpact} tone="warning">
            {copy.newDimensions} {preview.new_accounts + preview.new_departments + preview.new_cost_centers} ·{" "}
            {copy.replacedRecords} {preview.replaced_records}
          </Alert>
          {replaces ? (
            <label className="flex items-start gap-2 text-sm text-primary">
              <input
                type="checkbox"
                className="mt-1"
                checked={understood}
                onChange={(event) => setUnderstood(event.target.checked)}
              />
              {copy.understandReplace}
            </label>
          ) : null}
          <p className="text-sm text-secondary">{copy.replaceWarning}</p>
          <label className="flex items-center gap-2 text-sm text-secondary">
            <input
              type="checkbox"
              checked={createMissing}
              onChange={(event) => setCreateMissing(event.target.checked)}
            />
            {copy.createMissingDimensions}
          </label>
        </section>
      ) : null}

      {step === 5 && job ? (
        <section className="mt-6 space-y-4 rounded-surface border border-border bg-surface p-6">
          <Alert
            title={job.status === "applied" ? copy.importApplied : copy.importRejected}
            tone={job.status === "applied" ? "success" : "danger"}
          >
            {job.original_filename} · {copy.hashLabel} {job.sha256_short}
          </Alert>
          <div className="flex flex-wrap gap-3">
            <Link className="text-sm font-medium text-brand-600" href="/dashboard">
              {copy.goToDashboard}
            </Link>
            <Link className="text-sm font-medium text-brand-600" href={`/imports/job/?id=${job.id}`}>
              {copy.viewImportJob}
            </Link>
            {capabilities.can_manage_members ? (
              <Link className="text-sm font-medium text-brand-600" href="/audit">
                {copy.goToAudit}
              </Link>
            ) : null}
          </div>
        </section>
      ) : null}

      <div className="sticky bottom-0 mt-6 flex flex-wrap gap-2 border-t border-border bg-canvas py-4">
        {step > 1 && step < 5 ? (
          <Button variant="secondary" onClick={() => setStep((current) => current - 1)}>
            {copy.back}
          </Button>
        ) : null}
        {step === 2 ? (
          <Button
            disabled={busy || !job}
            loading={busy}
            onClick={() => {
              if (!job) return;
              setBusy(true);
              void validateImport(apiBaseUrl(), auth, job.id, {
                mapping,
                create_missing_dimensions: createMissing,
                amount_locale: amountLocale,
                sheet_name: sheetName || null,
                delimiter: delimiter || null,
              })
                .then(async (result) => {
                  setJob(result.data);
                  const [nextPreview, nextErrors] = await Promise.all([
                    previewImport(apiBaseUrl(), auth, job.id),
                    listImportErrors(apiBaseUrl(), auth, job.id),
                  ]);
                  setPreview(nextPreview.data);
                  setErrors(nextErrors.data.items);
                  trackEvent("import_validated", { import_type: importType });
                  setStep(3);
                })
                .catch((err: Error) => setError(err))
                .finally(() => setBusy(false));
            }}
          >
            {copy.previewTitle}
          </Button>
        ) : null}
        {step === 3 ? (
          <>
            <Button disabled={job?.error_count !== 0} onClick={() => setStep(4)}>
              {copy.continue}
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
          </>
        ) : null}
        {step === 4 ? (
          <Button
            disabled={!commitEnabled || busy}
            loading={busy}
            title={commitEnabled ? copy.commitImport : copy.commitBlocked}
            onClick={() => {
              if (!job) return;
              setBusy(true);
              void commitImport(apiBaseUrl(), auth, job.id)
                .then((result) => {
                  setJob(result.data);
                  trackEvent("import_applied", { import_type: importType });
                  setStep(5);
                })
                .catch((err: Error) => setError(err))
                .finally(() => setBusy(false));
            }}
          >
            {copy.commitImport}
          </Button>
        ) : null}
        {job && step < 5 ? (
          <Button
            variant="ghost"
            disabled={busy}
            onClick={() => {
              void cancelImport(apiBaseUrl(), auth, job.id).then((result) => setJob(result.data));
            }}
          >
            {copy.cancelImport}
          </Button>
        ) : null}
      </div>
    </CapabilityGate>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-surface border border-border p-3">
      <p className="text-xs text-secondary">{label}</p>
      <p className="mt-1 text-lg font-semibold text-primary">{value}</p>
    </div>
  );
}
