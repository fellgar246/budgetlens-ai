import { Suspense } from "react";

import { ImportJobRoute } from "@/features/imports/ImportJobRoute";

export default function Page() {
  return (
    <Suspense>
      <ImportJobRoute />
    </Suspense>
  );
}
