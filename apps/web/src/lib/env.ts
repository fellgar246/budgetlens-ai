export function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
}

export function appEnv(): string {
  return process.env.NEXT_PUBLIC_APP_ENV ?? "local";
}

export function authMode(): "dev" | "oidc" {
  return process.env.NEXT_PUBLIC_AUTH_MODE === "oidc" ? "oidc" : "dev";
}

export type OidcPublicConfig = {
  issuer: string;
  clientId: string;
  redirectUri: string;
  postLogoutRedirectUri: string;
  scopes: string;
};

export function oidcPublicConfig(): OidcPublicConfig {
  return {
    issuer: process.env.NEXT_PUBLIC_OIDC_ISSUER ?? "",
    clientId: process.env.NEXT_PUBLIC_OIDC_CLIENT_ID ?? "",
    redirectUri: process.env.NEXT_PUBLIC_OIDC_REDIRECT_URI ?? "",
    postLogoutRedirectUri: process.env.NEXT_PUBLIC_OIDC_POST_LOGOUT_REDIRECT_URI ?? "",
    scopes: process.env.NEXT_PUBLIC_OIDC_SCOPES ?? "openid profile email",
  };
}

export function resolvedOidcRedirectUri(): string {
  const configured = oidcPublicConfig().redirectUri.trim();
  if (configured) {
    return configured;
  }
  if (typeof window === "undefined") {
    return "";
  }
  return `${window.location.origin}/callback/`;
}

export function resolvedOidcLogoutUri(): string {
  const configured = oidcPublicConfig().postLogoutRedirectUri.trim();
  if (configured) {
    return configured;
  }
  if (typeof window === "undefined") {
    return "";
  }
  return `${window.location.origin}/login/`;
}

export function isProductionApp(): boolean {
  return appEnv() === "production";
}

export function appEnvLabel(): string {
  const value = appEnv();
  if (value === "test") {
    return "Pruebas";
  }
  if (value === "dev") {
    return "Desarrollo";
  }
  if (value === "production") {
    return "Producción";
  }
  return "Local";
}
