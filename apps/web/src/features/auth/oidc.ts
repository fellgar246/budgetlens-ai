import {
  oidcPublicConfig,
  resolvedOidcLogoutUri,
  resolvedOidcRedirectUri,
  type OidcPublicConfig,
} from "@/lib/env";

import { consumePkceSession, createPkceSession, persistPkceSession } from "./pkce";

export type OidcMetadata = {
  authorization_endpoint: string;
  token_endpoint: string;
  end_session_endpoint?: string;
};

export type OidcTokenResponse = {
  access_token: string;
  id_token?: string;
  token_type?: string;
  expires_in?: number;
};

export class OidcError extends Error {
  readonly reason: string;

  constructor(reason: string, message: string) {
    super(message);
    this.name = "OidcError";
    this.reason = reason;
  }
}

export function assertOidcConfig(
  config: OidcPublicConfig = oidcPublicConfig(),
): asserts config is OidcPublicConfig {
  if (!config.issuer.trim() || !config.clientId.trim()) {
    throw new OidcError("missing_config", "OIDC public configuration is incomplete.");
  }
}

export async function fetchOidcMetadata(
  issuer: string,
  fetchImpl: typeof fetch = fetch,
): Promise<OidcMetadata> {
  const base = issuer.replace(/\/$/, "");
  try {
    const response = await fetchImpl(`${base}/.well-known/openid-configuration`);
    if (response.ok) {
      const payload = (await response.json()) as Partial<OidcMetadata>;
      if (
        typeof payload.authorization_endpoint === "string" &&
        typeof payload.token_endpoint === "string"
      ) {
        return {
          authorization_endpoint: payload.authorization_endpoint,
          token_endpoint: payload.token_endpoint,
          end_session_endpoint:
            typeof payload.end_session_endpoint === "string"
              ? payload.end_session_endpoint
              : undefined,
        };
      }
    }
  } catch {
    // Fall back to the common authorization-server paths used by test issuers.
  }
  return {
    authorization_endpoint: `${base}/oauth2/authorize`,
    token_endpoint: `${base}/oauth2/token`,
    end_session_endpoint: `${base}/logout`,
  };
}

export function buildAuthorizationUrl(
  metadata: OidcMetadata,
  config: OidcPublicConfig,
  pkce: { challenge: string; state: string; nonce: string },
): string {
  const url = new URL(metadata.authorization_endpoint);
  url.searchParams.set("response_type", "code");
  url.searchParams.set("client_id", config.clientId);
  url.searchParams.set("redirect_uri", resolvedOidcRedirectUri() || config.redirectUri);
  url.searchParams.set("scope", config.scopes);
  url.searchParams.set("code_challenge", pkce.challenge);
  url.searchParams.set("code_challenge_method", "S256");
  url.searchParams.set("state", pkce.state);
  url.searchParams.set("nonce", pkce.nonce);
  return url.toString();
}

export function buildLogoutUrl(metadata: OidcMetadata, config: OidcPublicConfig): string | null {
  if (!metadata.end_session_endpoint) {
    return null;
  }
  const url = new URL(metadata.end_session_endpoint);
  const logoutUri = resolvedOidcLogoutUri() || config.postLogoutRedirectUri;
  url.searchParams.set("client_id", config.clientId);
  if (metadata.end_session_endpoint.includes("/logout")) {
    url.searchParams.set("logout_uri", logoutUri);
  } else {
    url.searchParams.set("post_logout_redirect_uri", logoutUri);
  }
  return url.toString();
}

export async function startAuthorization(fetchImpl: typeof fetch = fetch): Promise<string> {
  const config = oidcPublicConfig();
  assertOidcConfig(config);
  const metadata = await fetchOidcMetadata(config.issuer, fetchImpl);
  const pkce = await createPkceSession();
  persistPkceSession(pkce);
  return buildAuthorizationUrl(metadata, config, pkce);
}

export async function exchangeAuthorizationCode(
  currentUrl: URL,
  fetchImpl: typeof fetch = fetch,
): Promise<OidcTokenResponse> {
  const config = oidcPublicConfig();
  assertOidcConfig(config);
  const error = currentUrl.searchParams.get("error");
  if (error) {
    throw new OidcError("token_exchange", error);
  }
  const code = currentUrl.searchParams.get("code");
  const returnedState = currentUrl.searchParams.get("state");
  const stored = consumePkceSession();
  if (!code) {
    throw new OidcError("missing_code", "Authorization code is missing.");
  }
  if (!stored || stored.state !== returnedState) {
    throw new OidcError("state_mismatch", "Authorization state does not match.");
  }
  const metadata = await fetchOidcMetadata(config.issuer, fetchImpl);
  const body = new URLSearchParams({
    grant_type: "authorization_code",
    client_id: config.clientId,
    code,
    redirect_uri: resolvedOidcRedirectUri() || config.redirectUri,
    code_verifier: stored.verifier,
  });
  const response = await fetchImpl(metadata.token_endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    throw new OidcError("token_exchange", "Token endpoint rejected the authorization code.");
  }
  const tokens = (await response.json()) as Partial<OidcTokenResponse>;
  if (typeof tokens.access_token !== "string" || !tokens.access_token) {
    throw new OidcError("token_exchange", "Token endpoint did not return an access token.");
  }
  return { access_token: tokens.access_token, id_token: tokens.id_token };
}
