import { Suspense } from "react";

import { DashboardPage } from "@/features/dashboard/DashboardPage";

export default function Page() {
  return (
    <Suspense>
      <DashboardPage />
    </Suspense>
  );
}
