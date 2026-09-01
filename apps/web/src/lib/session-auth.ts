import type { AuthContext } from "@budgetlens/api-client";

import { getAccessToken } from "@/lib/access-token";

export function sessionAuth(userId: string, organizationId?: string | null): AuthContext {
  const token = getAccessToken() ?? userId;
  if (organizationId) {
    return { token, organizationId };
  }
  return { token };
}
