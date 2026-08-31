import type { VersionResponse } from "@budgetlens/api-client";

export type ComponentState = "ok" | "error" | "unknown";

export type HealthViewState =
  | { kind: "loading" }
  | {
      kind: "success";
      live: "ok";
      database: "ok";
      version: VersionResponse;
      checkedAt: string;
    }
  | {
      kind: "error";
      title: string;
      detail: string;
      traceId: string | null;
      live: ComponentState;
      database: ComponentState;
      version: VersionResponse | null;
      checkedAt: string;
    };
