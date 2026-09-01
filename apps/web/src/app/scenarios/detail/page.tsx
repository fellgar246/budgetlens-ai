import { Suspense } from "react";

import { ScenarioDetailRoute } from "@/features/scenarios/ScenarioDetailRoute";

export default function Page() {
  return (
    <Suspense>
      <ScenarioDetailRoute />
    </Suspense>
  );
}
