"use client";

import { useEffect, useMemo, useState } from "react";
import {
  listAccounts,
  listBudgetVersions,
  listCostCenters,
  listDepartments,
  type Account,
  type BudgetVersion,
  type CostCenter,
  type Department,
} from "@budgetlens/api-client";

import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";
import { useSession } from "@/features/session/SessionProvider";

export function useCatalogOptions() {
  const { userId, organizationId, generation } = useSession();
  const catalogKey = `${generation}:${userId}:${organizationId}`;
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [costCenters, setCostCenters] = useState<CostCenter[]>([]);
  const [versions, setVersions] = useState<BudgetVersion[]>([]);
  const [seenKey, setSeenKey] = useState(catalogKey);
  if (seenKey !== catalogKey) {
    setSeenKey(catalogKey);
    setAccounts([]);
    setDepartments([]);
    setCostCenters([]);
    setVersions([]);
  }

  useEffect(() => {
    if (!userId || !organizationId) {
      return;
    }
    let cancelled = false;
    const auth = sessionAuth(userId, organizationId);
    void Promise.all([
      listAccounts(apiBaseUrl(), auth),
      listDepartments(apiBaseUrl(), auth),
      listCostCenters(apiBaseUrl(), auth),
      listBudgetVersions(apiBaseUrl(), auth),
    ])
      .then(([nextAccounts, nextDepartments, nextCostCenters, nextVersions]) => {
        if (cancelled) return;
        setAccounts(nextAccounts.data.items);
        setDepartments(nextDepartments.data.items);
        setCostCenters(nextCostCenters.data.items);
        setVersions(nextVersions.data.items);
      })
      .catch(() => {
        if (cancelled) return;
        setAccounts([]);
        setDepartments([]);
        setCostCenters([]);
        setVersions([]);
      });
    return () => {
      cancelled = true;
    };
  }, [generation, organizationId, userId]);

  return useMemo(
    () => ({ accounts, departments, costCenters, versions }),
    [accounts, costCenters, departments, versions],
  );
}
