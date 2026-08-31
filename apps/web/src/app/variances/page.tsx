import { Suspense } from "react";

import { VariancesPage } from "@/features/variances/VariancesPage";

export default function Page() {
  return (
    <Suspense>
      <VariancesPage />
    </Suspense>
  );
}
