"use client";

import { personaLabel } from "@/lib/capabilities";
import { copy } from "@/lib/copy";
import { appEnvLabel } from "@/lib/env";
import { useSession } from "@/features/session/SessionProvider";

export function AppHeader({ onOpenNavigation }: { onOpenNavigation: () => void }) {
  const {
    users,
    organizations,
    userId,
    organizationId,
    selectedOrganization,
    me,
    switchNotice,
    setUserId,
    setOrganizationId,
  } = useSession();

  return (
    <header className="flex h-14 shrink-0 flex-col justify-center border-b border-border bg-surface md:h-16">
      <div className="flex flex-wrap items-center justify-between gap-3 px-4 md:px-8">
        <button
          type="button"
          className="h-10 text-sm font-medium text-brand-700 md:hidden"
          onClick={onOpenNavigation}
        >
          {copy.openNavigation}
        </button>
        <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
          <label className="flex min-w-40 flex-1 flex-col gap-1 text-xs md:max-w-64">
            <span className="font-medium text-secondary">{copy.selectUser}</span>
            <select
              className="h-10 rounded-control border border-border bg-white px-3 text-sm text-primary"
              value={userId}
              onChange={(event) => setUserId(event.target.value)}
            >
              <option value="">{copy.chooseUser}</option>
              {users.map((user) => (
                <option key={user.id} value={user.id}>
                  {user.display_name} · {user.email}
                </option>
              ))}
            </select>
          </label>
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
                  {organization.name} · {organization.role} · {organization.functional_currency}
                </option>
              ))}
            </select>
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          {selectedOrganization ? (
            <p className="hidden text-xs text-secondary md:block">
              {selectedOrganization.functional_currency} · {copy.fiscalStartLabel}{" "}
              {selectedOrganization.fiscal_year_start_month}
            </p>
          ) : null}
          {me?.persona ? (
            <p className="hidden text-xs text-secondary lg:block">{personaLabel(me.persona)}</p>
          ) : null}
          <span className="rounded-full bg-canvas px-3 py-1 text-xs font-medium text-primary">
            {appEnvLabel()}
          </span>
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
