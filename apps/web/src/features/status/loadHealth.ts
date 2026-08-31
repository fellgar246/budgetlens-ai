import { getLive, getReady, getVersion } from "@budgetlens/api-client";

import { copy } from "@/lib/copy";

import type { HealthViewState } from "./types";

function nowIso(): string {
  return new Date().toISOString();
}

export async function loadHealth(baseUrl: string): Promise<HealthViewState> {
  try {
    const [live, ready, version] = await Promise.all([
      getLive(baseUrl),
      getReady(baseUrl),
      getVersion(baseUrl),
    ]);

    if (live.status === 200 && ready.status === 200 && version.status === 200) {
      return {
        kind: "success",
        live: "ok",
        database: "ok",
        version: version.data,
        checkedAt: nowIso(),
      };
    }

    const traceId = ready.traceId ?? live.traceId ?? version.traceId;
    return {
      kind: "error",
      title: copy.degraded,
      detail: copy.degradedDetail,
      traceId,
      live: live.status === 200 ? "ok" : "error",
      database: ready.data?.components?.database === "ok" ? "ok" : "error",
      version: version.status === 200 ? version.data : null,
      checkedAt: nowIso(),
    };
  } catch (error) {
    const traceId =
      error instanceof Error && "traceId" in error ? (error.traceId as string | null) : null;
    return {
      kind: "error",
      title: copy.unavailable,
      detail: copy.unavailableDetail,
      traceId,
      live: "error",
      database: "unknown",
      version: null,
      checkedAt: nowIso(),
    };
  }
}
