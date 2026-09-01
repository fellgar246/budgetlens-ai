"use client";

import { useSearchParams } from "next/navigation";

import { ScenarioBuilderPage } from "./ScenarioBuilderPage";

export function ScenarioDetailRoute() {
  const scenarioId = useSearchParams().get("id") ?? undefined;
  return <ScenarioBuilderPage scenarioId={scenarioId} />;
}
