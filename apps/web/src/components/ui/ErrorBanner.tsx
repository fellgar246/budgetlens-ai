"use client";

import { useState } from "react";
import { ApiRequestError } from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { copy } from "@/lib/copy";

export function ErrorBanner({
  error,
  onRetry,
}: {
  error: string | Error | null;
  onRetry?: () => void;
}) {
  const [copied, setCopied] = useState(false);
  if (!error) {
    return null;
  }
  const message = typeof error === "string" ? error : error.message;
  const traceId = error instanceof ApiRequestError ? error.traceId : null;
  return (
    <div role="alert" className="mt-6 rounded-surface border border-border bg-surface p-4">
      <p className="text-sm text-danger">{message}</p>
      <p className="mt-2 text-sm text-secondary">{copy.errorCorrective}</p>
      {traceId ? (
        <p className="mt-2 text-xs text-secondary">
          {copy.traceLabel}: <code className="text-primary">{traceId}</code>
          <Button
            variant="link"
            className="ml-3"
            onClick={() => {
              void navigator.clipboard.writeText(traceId).then(() => {
                setCopied(true);
                window.setTimeout(() => setCopied(false), 2000);
              });
            }}
          >
            {copied ? copy.copied : copy.copyTrace}
          </Button>
        </p>
      ) : null}
      {onRetry ? (
        <div className="mt-3">
          <Button variant="secondary" onClick={onRetry}>
            {copy.retry}
          </Button>
        </div>
      ) : null}
    </div>
  );
}
