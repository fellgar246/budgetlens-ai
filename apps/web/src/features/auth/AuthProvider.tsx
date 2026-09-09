"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getMe } from "@budgetlens/api-client";

import { clearAccessToken, getAccessToken, setAccessToken } from "@/lib/access-token";
import { readDevUserId, writeDevSession } from "@/lib/dev-session";
import { apiBaseUrl, authMode, type OidcPublicConfig, oidcPublicConfig } from "@/lib/env";

import {
  OidcError,
  buildLogoutUrl,
  exchangeAuthorizationCode,
  fetchOidcMetadata,
  startAuthorization,
} from "./oidc";

type AuthContextValue = {
  mode: "dev" | "oidc";
  ready: boolean;
  userId: string;
  beginLogin: () => Promise<void>;
  completeCallback: (currentUrl: URL) => Promise<void>;
  signOut: () => Promise<void>;
  setDevUserId: (userId: string) => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const mode = authMode();
  const [ready, setReady] = useState(false);
  const [userId, setUserId] = useState("");

  useEffect(() => {
    if (mode === "oidc" && !getAccessToken()) {
      setUserId("");
      writeDevSession(null, null);
      setReady(true);
      return;
    }
    setUserId(readDevUserId() ?? "");
    setReady(true);
  }, [mode]);

  const setDevUserId = useCallback(
    (next: string) => {
      if (mode !== "dev") {
        return;
      }
      setUserId(next);
      writeDevSession(next || null, null);
    },
    [mode],
  );

  const beginLogin = useCallback(async () => {
    if (mode !== "oidc") {
      return;
    }
    const authorizationUrl = await startAuthorization();
    window.location.assign(authorizationUrl);
  }, [mode]);

  const completeCallback = useCallback(async (currentUrl: URL) => {
    const tokens = await exchangeAuthorizationCode(currentUrl);
    setAccessToken(tokens.access_token);
    const me = await getMe(apiBaseUrl(), { token: tokens.access_token });
    setUserId(me.data.id);
    writeDevSession(me.data.id, null);
  }, []);

  const signOut = useCallback(async () => {
    const config: OidcPublicConfig = oidcPublicConfig();
    clearAccessToken();
    setUserId("");
    writeDevSession(null, null);
    if (mode !== "oidc" || !config.issuer || !config.clientId) {
      return;
    }
    try {
      const metadata = await fetchOidcMetadata(config.issuer);
      const logoutUrl = buildLogoutUrl(metadata, config);
      if (logoutUrl) {
        window.location.assign(logoutUrl);
      }
    } catch (error) {
      if (!(error instanceof OidcError)) {
        throw error;
      }
    }
  }, [mode]);

  const value = useMemo<AuthContextValue>(
    () => ({
      mode,
      ready,
      userId,
      beginLogin,
      completeCallback,
      signOut,
      setDevUserId,
    }),
    [beginLogin, completeCallback, mode, ready, setDevUserId, signOut, userId],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const value = useContext(AuthContext);
  if (value === null) {
    throw new Error("useAuth requires AuthProvider");
  }
  return value;
}
