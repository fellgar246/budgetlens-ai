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
import { usePathname, useRouter } from "next/navigation";
import {
  getDevIdentities,
  getMe,
  listOrganizations,
  type Capabilities,
  type DevIdentity,
  type MeResponse,
  type Organization,
} from "@budgetlens/api-client";

import {
  EMPTY_ANALYSIS_FILTERS,
  clearStoredFilters,
  writeStoredFilters,
} from "@/lib/analysis-filters";
import { EMPTY_CAPABILITIES } from "@/lib/capabilities";
import { copy } from "@/lib/copy";
import { readDevOrganizationId, readDevUserId, writeDevSession } from "@/lib/dev-session";
import { apiBaseUrl } from "@/lib/env";

type SessionContextValue = {
  userId: string;
  organizationId: string;
  users: DevIdentity[];
  organizations: Organization[];
  me: MeResponse | null;
  capabilities: Capabilities;
  selectedOrganization: Organization | undefined;
  generation: number;
  switchNotice: string | null;
  setUserId: (userId: string) => void;
  setOrganizationId: (organizationId: string) => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [users, setUsers] = useState<DevIdentity[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [userId, setUserIdState] = useState("");
  const [organizationId, setOrganizationIdState] = useState("");
  const [me, setMe] = useState<MeResponse | null>(null);
  const [generation, setGeneration] = useState(0);
  const [switchNotice, setSwitchNotice] = useState<string | null>(null);

  useEffect(() => {
    setUserIdState(readDevUserId() ?? "");
    setOrganizationIdState(readDevOrganizationId() ?? "");
    void getDevIdentities(apiBaseUrl())
      .then((result) => setUsers(result.data.users))
      .catch(() => setUsers([]));
  }, []);

  useEffect(() => {
    if (!userId) {
      setOrganizations([]);
      setMe(null);
      return;
    }
    const loadOrganizations = () => {
      void listOrganizations(apiBaseUrl(), { token: userId })
        .then((result) => {
          setOrganizations(result.data.items);
          if (organizationId && !result.data.items.some((item) => item.id === organizationId)) {
            setOrganizationIdState("");
            writeDevSession(userId, null);
          }
        })
        .catch(() => setOrganizations([]));
    };
    loadOrganizations();
    window.addEventListener("budgetlens-session", loadOrganizations);
    return () => window.removeEventListener("budgetlens-session", loadOrganizations);
  }, [userId, organizationId]);

  useEffect(() => {
    if (!userId) {
      setMe(null);
      return;
    }
    const loadMe = () => {
      void getMe(apiBaseUrl(), {
        token: userId,
        organizationId: organizationId || undefined,
      })
        .then((result) => setMe(result.data))
        .catch(() => setMe(null));
    };
    loadMe();
    window.addEventListener("budgetlens-session", loadMe);
    return () => window.removeEventListener("budgetlens-session", loadMe);
  }, [userId, organizationId, generation]);

  const clearViewContext = useCallback(
    (nextOrganizationId: string | null) => {
      clearStoredFilters(organizationId);
      setMe(null);
      setGeneration((current) => current + 1);
      if (typeof window !== "undefined" && window.location.search) {
        router.replace(pathname || "/");
      }
      if (nextOrganizationId) {
        writeStoredFilters(nextOrganizationId, EMPTY_ANALYSIS_FILTERS);
      }
    },
    [organizationId, pathname, router],
  );

  const setUserId = useCallback(
    (next: string) => {
      setUserIdState(next);
      setOrganizationIdState("");
      writeDevSession(next || null, null);
      clearViewContext(null);
      window.dispatchEvent(new Event("budgetlens-session"));
    },
    [clearViewContext],
  );

  const setOrganizationId = useCallback(
    (next: string) => {
      const selected = organizations.find((item) => item.id === next);
      setOrganizationIdState(next);
      writeDevSession(userId || null, next || null);
      clearViewContext(next || null);
      if (selected) {
        setSwitchNotice(`${copy.switchedOrganization} ${selected.name}`);
        window.setTimeout(() => setSwitchNotice(null), 4000);
      } else {
        setSwitchNotice(null);
      }
      window.dispatchEvent(new Event("budgetlens-session"));
    },
    [clearViewContext, organizations, userId],
  );

  const value = useMemo<SessionContextValue>(
    () => ({
      userId,
      organizationId,
      users,
      organizations,
      me,
      capabilities: me?.capabilities ?? EMPTY_CAPABILITIES,
      selectedOrganization: organizations.find((item) => item.id === organizationId),
      generation,
      switchNotice,
      setUserId,
      setOrganizationId,
    }),
    [
      generation,
      me,
      organizationId,
      organizations,
      setOrganizationId,
      setUserId,
      switchNotice,
      userId,
      users,
    ],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): SessionContextValue {
  const value = useContext(SessionContext);
  if (value === null) {
    throw new Error("useSession requires SessionProvider");
  }
  return value;
}
