import { afterEach, expect, test, vi } from "vitest";

import { clearAccessToken, getAccessToken, setAccessToken } from "@/lib/access-token";
import { sessionAuth } from "@/lib/session-auth";

afterEach(() => {
  clearAccessToken();
});

test("access token stays in memory and is not written to storage", () => {
  const storage: Record<string, string> = {};
  vi.stubGlobal("localStorage", {
    getItem: (key: string) => storage[key] ?? null,
    setItem: (key: string, value: string) => {
      storage[key] = value;
    },
    removeItem: (key: string) => {
      delete storage[key];
    },
  });
  setAccessToken("oidc-access-token");
  expect(getAccessToken()).toBe("oidc-access-token");
  expect(storage).toEqual({});
  clearAccessToken();
  expect(getAccessToken()).toBeNull();
});

test("session auth prefers the in-memory token over the local user id", () => {
  expect(sessionAuth("local-user", "org-1")).toEqual({
    token: "local-user",
    organizationId: "org-1",
  });
  setAccessToken("oidc-access-token");
  expect(sessionAuth("local-user", "org-1")).toEqual({
    token: "oidc-access-token",
    organizationId: "org-1",
  });
});
