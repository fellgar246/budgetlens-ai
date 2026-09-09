import { afterEach, expect, test, vi } from "vitest";

import { clearAccessToken, getAccessToken } from "@/lib/access-token";
import {
  buildAuthorizationUrl,
  buildLogoutUrl,
  exchangeAuthorizationCode,
  fetchOidcMetadata,
} from "@/features/auth/oidc";
import { consumePkceSession, createPkceSession, persistPkceSession } from "@/features/auth/pkce";

afterEach(() => {
  clearAccessToken();
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

test("pkce verifier stays in session storage and never writes the access token", async () => {
  const storage: Record<string, string> = {};
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => storage[key] ?? null,
    setItem: (key: string, value: string) => {
      storage[key] = value;
    },
    removeItem: (key: string) => {
      delete storage[key];
    },
  });
  vi.stubGlobal("localStorage", {
    getItem: () => null,
    setItem: () => {
      throw new Error("must not persist tokens in localStorage");
    },
    removeItem: () => undefined,
  });
  const pkce = await createPkceSession();
  persistPkceSession(pkce);
  expect(storage["budgetlens.oidc.pkce"]).toContain(pkce.verifier);
  expect(storage["budgetlens.oidc.pkce"]).not.toContain("access_token");
  const consumed = consumePkceSession();
  expect(consumed?.verifier).toBe(pkce.verifier);
  expect(storage["budgetlens.oidc.pkce"]).toBeUndefined();
  expect(getAccessToken()).toBeNull();
});

test("authorization url uses pkce and public client fields only", () => {
  const url = buildAuthorizationUrl(
    {
      authorization_endpoint: "https://issuer.example/oauth2/authorize",
      token_endpoint: "https://issuer.example/oauth2/token",
    },
    {
      issuer: "https://issuer.example",
      clientId: "web-client",
      redirectUri: "http://localhost:3000/callback/",
      postLogoutRedirectUri: "http://localhost:3000/login/",
      scopes: "openid profile email",
    },
    { challenge: "abc", state: "state-1", nonce: "nonce-1" },
  );
  const parsed = new URL(url);
  expect(parsed.searchParams.get("client_id")).toBe("web-client");
  expect(parsed.searchParams.get("code_challenge")).toBe("abc");
  expect(parsed.searchParams.get("code_challenge_method")).toBe("S256");
  expect(parsed.searchParams.get("response_type")).toBe("code");
  expect(url).not.toContain("client_secret");
});

test("token exchange rejects a state mismatch and does not keep the verifier", async () => {
  const storage: Record<string, string> = {};
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => storage[key] ?? null,
    setItem: (key: string, value: string) => {
      storage[key] = value;
    },
    removeItem: (key: string) => {
      delete storage[key];
    },
  });
  persistPkceSession({ verifier: "verifier-1", state: "expected", nonce: "nonce-1" });
  vi.stubEnv("NEXT_PUBLIC_OIDC_ISSUER", "https://issuer.example");
  vi.stubEnv("NEXT_PUBLIC_OIDC_CLIENT_ID", "web-client");
  await expect(
    exchangeAuthorizationCode(
      new URL("http://localhost:3000/callback/?code=abc&state=other"),
      vi.fn() as unknown as typeof fetch,
    ),
  ).rejects.toMatchObject({ reason: "state_mismatch" });
  expect(storage["budgetlens.oidc.pkce"]).toBeUndefined();
});

test("discovery falls back to oauth2 paths when well-known is unavailable", async () => {
  const fetchImpl = vi.fn().mockRejectedValue(new Error("offline"));
  const metadata = await fetchOidcMetadata("https://issuer.example/pool", fetchImpl);
  expect(metadata.authorization_endpoint).toBe("https://issuer.example/pool/oauth2/authorize");
  expect(metadata.token_endpoint).toBe("https://issuer.example/pool/oauth2/token");
  const logout = buildLogoutUrl(metadata, {
    issuer: "https://issuer.example/pool",
    clientId: "web-client",
    redirectUri: "http://localhost:3000/callback/",
    postLogoutRedirectUri: "http://localhost:3000/login/",
    scopes: "openid",
  });
  expect(logout).toContain("client_id=web-client");
  expect(logout).toContain("logout_uri=");
});
