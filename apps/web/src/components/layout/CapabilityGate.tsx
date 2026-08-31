import type { ReactNode } from "react";

import { copy } from "@/lib/copy";

import { EmptyState } from "./EmptyState";

export function CapabilityGate({
  allowed,
  needsSession = true,
  hasSession,
  children,
}: {
  allowed: boolean;
  needsSession?: boolean;
  hasSession: boolean;
  children: ReactNode;
}) {
  if (needsSession && !hasSession) {
    return <EmptyState title={copy.sessionNeededGeneric} detail={copy.chooseUser} />;
  }
  if (!allowed) {
    return <EmptyState title={copy.forbiddenTitle} detail={copy.forbiddenDetail} />;
  }
  return children;
}
