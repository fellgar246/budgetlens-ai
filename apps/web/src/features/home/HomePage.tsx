"use client";

import { DashboardPage } from "@/features/dashboard/DashboardPage";
import { OpsPage } from "@/features/ops/OpsPage";
import { useSession } from "@/features/session/SessionProvider";

export function HomePage() {
  const { capabilities, userId } = useSession();
  if (userId && capabilities.can_view_technical_metrics && !capabilities.can_view_dashboard) {
    return <OpsPage requireOperator />;
  }
  return <DashboardPage />;
}
