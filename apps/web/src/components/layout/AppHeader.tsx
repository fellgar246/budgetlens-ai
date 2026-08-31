"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  getDevIdentities,
  listOrganizations,
  type DevIdentity,
  type Organization,
} from "@budgetlens/api-client";

import { copy } from "@/lib/copy";
import { readDevOrganizationId, readDevUserId, writeDevSession } from "@/lib/dev-session";
import { apiBaseUrl, appEnvLabel } from "@/lib/env";

export function AppHeader() {
  const pathname = usePathname();
  const [users, setUsers] = useState<DevIdentity[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [userId, setUserId] = useState<string>("");
  const [organizationId, setOrganizationId] = useState<string>("");

  useEffect(() => {
    setUserId(readDevUserId() ?? "");
    setOrganizationId(readDevOrganizationId() ?? "");
    void getDevIdentities(apiBaseUrl())
      .then((result) => setUsers(result.data.users))
      .catch(() => setUsers([]));
  }, []);

  useEffect(() => {
    if (!userId) {
      setOrganizations([]);
      return;
    }
    void listOrganizations(apiBaseUrl(), { token: userId })
      .then((result) => {
        setOrganizations(result.data.items);
        if (organizationId && !result.data.items.some((item) => item.id === organizationId)) {
          setOrganizationId("");
          writeDevSession(userId, null);
        }
      })
      .catch(() => setOrganizations([]));
  }, [userId, organizationId]);

  const selectedOrg = organizations.find((item) => item.id === organizationId);

  return (
    <header className="border-b border-border bg-brand-700 text-white">
      <div className="flex h-16 items-center justify-between gap-4 px-4 md:px-8">
        <div className="flex items-center gap-6">
          <p className="text-lg font-semibold tracking-tight">{copy.appName}</p>
          <nav aria-label="Principal" className="flex items-center gap-4 text-sm font-medium">
            <Link
              href="/"
              className={pathname === "/" ? "text-white" : "text-white/80 hover:text-white"}
            >
              {copy.navStatus}
            </Link>
            <Link
              href="/catalogo"
              className={pathname === "/catalogo" ? "text-white" : "text-white/80 hover:text-white"}
            >
              {copy.navCatalog}
            </Link>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          {selectedOrg ? (
            <p className="hidden text-xs text-white/80 md:block">
              {selectedOrg.functional_currency} · {copy.fiscalStartLabel}{" "}
              {selectedOrg.fiscal_year_start_month}
            </p>
          ) : null}
          <span className="rounded-full bg-white/15 px-3 py-1 text-xs font-medium">
            {appEnvLabel()}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-3 border-t border-white/15 bg-[#102536] px-4 py-3 md:px-8">
        <label className="flex min-w-48 flex-1 flex-col gap-1 text-xs">
          <span className="font-medium text-white/80">{copy.selectUser}</span>
          <select
            className="h-10 rounded-control border border-white/20 bg-[#14324b] px-3 text-sm text-white"
            value={userId}
            onChange={(event) => {
              const next = event.target.value;
              setUserId(next);
              setOrganizationId("");
              writeDevSession(next || null, null);
              window.dispatchEvent(new Event("budgetlens-session"));
            }}
          >
            <option value="">{copy.chooseUser}</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.display_name} · {user.email}
              </option>
            ))}
          </select>
        </label>
        <label className="flex min-w-48 flex-1 flex-col gap-1 text-xs">
          <span className="font-medium text-white/80">{copy.selectOrganization}</span>
          <select
            className="h-10 rounded-control border border-white/20 bg-[#14324b] px-3 text-sm text-white"
            value={organizationId}
            disabled={!userId}
            onChange={(event) => {
              const next = event.target.value;
              setOrganizationId(next);
              writeDevSession(userId || null, next || null);
              window.dispatchEvent(new Event("budgetlens-session"));
            }}
          >
            <option value="">{copy.chooseOrganization}</option>
            {organizations.map((organization) => (
              <option key={organization.id} value={organization.id}>
                {organization.name} · {organization.role} · {organization.functional_currency}
              </option>
            ))}
          </select>
        </label>
      </div>
    </header>
  );
}
