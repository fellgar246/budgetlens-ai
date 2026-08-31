import { Suspense } from "react";

import { CopilotPage } from "@/features/copilot/CopilotPage";

export default function Page() {
  return (
    <Suspense>
      <CopilotPage />
    </Suspense>
  );
}
