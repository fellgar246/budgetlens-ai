"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { personaLabel } from "@/lib/capabilities";
import { copy } from "@/lib/copy";
import { appEnvLabel, isProductionApp } from "@/lib/env";
import { useSession } from "@/features/session/SessionProvider";

const MONTHS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];

export function AppHeader({ onOpenNavigation }: { onOpenNavigation: () => void }) {
  const {
    users,
    organizations,
    userId,
    organizationId,
    selectedOrganization,
    me,
    switchNotice,
    setOrganizationId,
  } = useSession();
  const router = useRouter();
  const currentUser = users.find((user) => user.id === userId);

  return (
    <header className="flex h-14 shrink-0 flex-col justify-center border-b border-border bg-surface md:h-16">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 md:px-8">
        <div className="flex items-center gap-3">
          <button
            type="button"
            className="h-10 text-sm font-medium text-brand-700 lg:hidden"
            onClick={onOpenNavigation}
          >
            {copy.openNavigation}
          </button>
          <p className="text-sm font-semibold text-brand-700 lg:hidden">{copy.appName}</p>
        </div>
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
          <label className="flex min-w-40 flex-1 flex-col gap-1 text-xs md:max-w-64">
            <span className="font-medium text-secondary">{copy.selectOrganization}</span>
            <select
              className="h-10 rounded-control border border-border bg-white px-3 text-sm text-primary"
              value={organizationId}
              disabled={!userId || organizations.length === 0}
              onChange={(event) => setOrganizationId(event.target.value)}
            >
              <option value="">
                {userId && organizations.length === 0
                  ? copy.noOrganizations
                  : copy.chooseOrganization}
              </option>
              {organizations.map((organization) => (
                <option key={organization.id} value={organization.id}>
                  {organization.name} · {organization.functional_currency}
                </option>
              ))}
            </select>
          </label>
          {selectedOrganization ? (
            <p className="text-xs text-secondary">
              {copy.fiscalPeriodLabel}: {MONTHS[selectedOrganization.fiscal_year_start_month - 1]} ·{" "}
              {selectedOrganization.functional_currency}
            </p>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {!isProductionApp() ? (
            <span className="rounded-pill bg-canvas px-3 py-1 text-xs font-medium text-primary">
              {appEnvLabel()}
            </span>
          ) : null}
          <details className="relative">
            <summary className="flex h-10 cursor-pointer list-none items-center rounded-control px-3 text-sm font-medium text-primary">
              {me?.display_name ?? currentUser?.display_name ?? copy.profileLabel}
            </summary>
            <div className="absolute right-0 z-20 mt-2 w-64 rounded-surface border border-border bg-surface p-3 shadow-overlay">
              <p className="text-sm text-primary">
                {me?.email ?? currentUser?.email ?? copy.chooseUser}
              </p>
              {me?.persona ? (
                <p className="mt-1 text-xs text-secondary">{personaLabel(me.persona)}</p>
              ) : null}
              <div className="mt-3 flex flex-col gap-2">
                <Link className="text-sm font-medium text-brand-600" href="/login">
                  {copy.changeUser}
                </Link>
                <Link className="text-sm font-medium text-brand-600" href="/select-organization">
                  {copy.changeOrganization}
                </Link>
                <button
                  type="button"
                  className="h-10 text-left text-sm font-medium text-danger"
                  onClick={() => router.push("/logout/")}
                >
                  {copy.signOut}
                </button>
              </div>
            </div>
          </details>
        </div>
      </div>
      {switchNotice ? (
        <p
          className="border-t border-border bg-canvas px-4 py-2 text-xs text-primary md:px-8"
          role="status"
        >
          {switchNotice}
        </p>
      ) : null}
    </header>
  );
}
