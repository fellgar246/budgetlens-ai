"use client";

import { useEffect, useState } from "react";
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
import { useSession } from "@/features/session/SessionProvider";

export function useCatalogOptions() {
  const { userId, organizationId, generation } = useSession();
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [costCenters, setCostCenters] = useState<CostCenter[]>([]);
  const [versions, setVersions] = useState<BudgetVersion[]>([]);

  useEffect(() => {
    setAccounts([]);
    setDepartments([]);
    setCostCenters([]);
    setVersions([]);
    if (!userId || !organizationId) {
      return;
    }
    const auth = { token: userId, organizationId };
    void Promise.all([
      listAccounts(apiBaseUrl(), auth),
      listDepartments(apiBaseUrl(), auth),
      listCostCenters(apiBaseUrl(), auth),
      listBudgetVersions(apiBaseUrl(), auth),
    ])
      .then(([nextAccounts, nextDepartments, nextCostCenters, nextVersions]) => {
        setAccounts(nextAccounts.data.items);
        setDepartments(nextDepartments.data.items);
        setCostCenters(nextCostCenters.data.items);
        setVersions(nextVersions.data.items);
      })
      .catch(() => {
        setAccounts([]);
        setDepartments([]);
        setCostCenters([]);
        setVersions([]);
      });
  }, [generation, organizationId, userId]);

  return { accounts, departments, costCenters, versions };
}
