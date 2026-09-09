const PKCE_KEY = "budgetlens.oidc.pkce";

export type PkceSession = {
  verifier: string;
  state: string;
  nonce: string;
};

function base64UrlEncode(bytes: Uint8Array): string {
  let binary = "";
  bytes.forEach((value) => {
    binary += String.fromCharCode(value);
  });
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

export function randomUrlSafe(byteLength = 32): string {
  return base64UrlEncode(crypto.getRandomValues(new Uint8Array(byteLength)));
}

export async function createPkceSession(): Promise<PkceSession & { challenge: string }> {
  const verifier = randomUrlSafe(32);
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return {
    verifier,
    state: randomUrlSafe(16),
    nonce: randomUrlSafe(16),
    challenge: base64UrlEncode(new Uint8Array(digest)),
  };
}

export function persistPkceSession(session: PkceSession): void {
  window.sessionStorage.setItem(PKCE_KEY, JSON.stringify(session));
}

export function consumePkceSession(): PkceSession | null {
  const raw = window.sessionStorage.getItem(PKCE_KEY);
  window.sessionStorage.removeItem(PKCE_KEY);
  if (!raw) {
    return null;
  }
  try {
    const parsed = JSON.parse(raw) as Partial<PkceSession>;
    if (
      typeof parsed.verifier === "string" &&
      typeof parsed.state === "string" &&
      typeof parsed.nonce === "string"
    ) {
      return { verifier: parsed.verifier, state: parsed.state, nonce: parsed.nonce };
    }
  } catch {
    return null;
  }
  return null;
}
