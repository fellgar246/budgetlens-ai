"use client";

import { useCallback, useEffect, useState } from "react";

import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";

import { HealthCard } from "./HealthCard";
import { loadHealth } from "./loadHealth";
import type { HealthViewState } from "./types";

export function StatusPage({ embedded = false }: { embedded?: boolean }) {
  const [state, setState] = useState<HealthViewState>({ kind: "loading" });
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setState({ kind: "loading" });
    const next = await loadHealth(apiBaseUrl());
    setState(next);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  async function handleCopyTrace() {
    if (state.kind !== "error" || !state.traceId) {
      return;
    }
    try {
      await navigator.clipboard.writeText(state.traceId);
      setCopyFeedback(copy.copied);
      window.setTimeout(() => setCopyFeedback(null), 2000);
    } catch {
      setCopyFeedback(copy.copyTrace);
    }
  }

  return (
    <div className={embedded ? "w-full" : "mx-auto w-full max-w-3xl"}>
      {embedded ? null : (
        <>
          <p className="text-sm font-medium text-secondary">{copy.appName}</p>
          <h1 className="mt-2 text-[28px] font-semibold leading-9 text-primary">
            {copy.statusTitle}
          </h1>
          <p className="mt-2 max-w-2xl text-base text-secondary">{copy.statusDescription}</p>
        </>
      )}
      <div className={embedded ? "" : "mt-8"}>
        <HealthCard
          state={state}
          onRetry={() => {
            void refresh();
          }}
          onCopyTrace={() => {
            void handleCopyTrace();
          }}
          copyFeedback={copyFeedback}
        />
      </div>
    </div>
  );
}
