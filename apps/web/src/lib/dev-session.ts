const USER_KEY = "budgetlens.dev.userId";
const ORG_KEY = "budgetlens.dev.organizationId";

export function readDevUserId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(USER_KEY);
}

export function readDevOrganizationId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  return window.sessionStorage.getItem(ORG_KEY);
}

export function writeDevSession(userId: string | null, organizationId: string | null): void {
  if (typeof window === "undefined") {
    return;
  }
  if (userId) {
    window.sessionStorage.setItem(USER_KEY, userId);
  } else {
    window.sessionStorage.removeItem(USER_KEY);
  }
  if (organizationId) {
    window.sessionStorage.setItem(ORG_KEY, organizationId);
  } else {
    window.sessionStorage.removeItem(ORG_KEY);
  }
}
