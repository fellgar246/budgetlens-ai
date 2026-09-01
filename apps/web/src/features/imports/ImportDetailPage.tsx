"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { getImport, type ImportJob } from "@budgetlens/api-client";

import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Alert } from "@/components/ui/Alert";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { PageHeader } from "@/components/layout/PageHeader";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";

export function ImportDetailPage({ jobId }: { jobId: string }) {
  const { userId, organizationId, capabilities } = useSession();
  const [job, setJob] = useState<ImportJob | null>(null);
  const [error, setError] = useState<Error | string | null>(null);
  const hasSession = Boolean(userId && organizationId);

  useEffect(() => {
    if (!userId || !organizationId) return;
    void getImport(apiBaseUrl(), sessionAuth(userId, organizationId), jobId)
      .then((result) => setJob(result.data))
      .catch((err: Error) => setError(err));
  }, [jobId, organizationId, userId]);

  return (
    <CapabilityGate allowed={capabilities.can_import} hasSession={hasSession}>
      <PageHeader title={copy.importsTitle} description={copy.importsDescription} />
      <ErrorBanner error={error} />
      {job ? (
        <section className="mt-6 space-y-4 rounded-surface border border-border bg-surface p-6">
          <Alert
            title={job.status === "applied" ? copy.importApplied : job.status}
            tone={job.status === "applied" ? "success" : "info"}
          >
            {job.original_filename} · {copy.hashLabel} {job.sha256_short} · {copy.fileSize}{" "}
            {job.size_bytes} B
          </Alert>
          <p className="text-sm text-secondary">
            {job.valid_count}/{job.row_count} · {copy.errorRows} {job.error_count} · {copy.warningRows}{" "}
            {job.warning_count}
          </p>
          <div className="flex flex-wrap gap-3">
            <Link className="text-sm font-medium text-brand-600" href="/dashboard">
              {copy.goToDashboard}
            </Link>
            <Link className="text-sm font-medium text-brand-600" href="/imports">
              {copy.navImports}
            </Link>
            {capabilities.can_manage_members ? (
              <Link className="text-sm font-medium text-brand-600" href="/audit">
                {copy.goToAudit}
              </Link>
            ) : null}
          </div>
        </section>
      ) : null}
    </CapabilityGate>
  );
}
