"use client";

import { useSearchParams } from "next/navigation";

import { ImportDetailPage } from "./ImportDetailPage";

export function ImportJobRoute() {
  const jobId = useSearchParams().get("id") ?? "";
  return <ImportDetailPage jobId={jobId} />;
}
