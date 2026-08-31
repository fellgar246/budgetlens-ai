"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ApiRequestError,
  activateBudgetVersion,
  archiveBudgetVersion,
  createAccount,
  createBudgetVersion,
  createCostCenter,
  createDepartment,
  getMe,
  listAccounts,
  listBudgetVersions,
  listCostCenters,
  listDepartments,
  publishBudgetVersion,
  type Account,
  type BudgetVersion,
  type CostCenter,
  type Department,
  type MeResponse,
} from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { personaLabel } from "@/lib/capabilities";
import { copy } from "@/lib/copy";
import { readDevOrganizationId, readDevUserId } from "@/lib/dev-session";
import { apiBaseUrl } from "@/lib/env";

type CatalogState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "error"; message: string; traceId: string | null }
  | {
      kind: "ready";
      me: MeResponse;
      accounts: Account[];
      departments: Department[];
      costCenters: CostCenter[];
      versions: BudgetVersion[];
    };

function auth() {
  const token = readDevUserId();
  const organizationId = readDevOrganizationId();
  if (!token || !organizationId) {
    return null;
  }
  return { token, organizationId };
}

export function CatalogPage() {
  const [state, setState] = useState<CatalogState>({ kind: "idle" });
  const [accountForm, setAccountForm] = useState({ code: "", name: "", account_type: "expense" });
  const [departmentForm, setDepartmentForm] = useState({ code: "", name: "" });
  const [costCenterForm, setCostCenterForm] = useState({ code: "", name: "" });
  const [versionForm, setVersionForm] = useState({ name: "", fiscal_year: "2026" });

  const refresh = useCallback(async () => {
    const context = auth();
    if (!context) {
      setState({ kind: "idle" });
      return;
    }
    setState({ kind: "loading" });
    try {
      const [me, accounts, departments, costCenters, versions] = await Promise.all([
        getMe(apiBaseUrl(), context),
        listAccounts(apiBaseUrl(), context),
        listDepartments(apiBaseUrl(), context),
        listCostCenters(apiBaseUrl(), context),
        listBudgetVersions(apiBaseUrl(), context),
      ]);
      setState({
        kind: "ready",
        me: me.data,
        accounts: accounts.data.items,
        departments: departments.data.items,
        costCenters: costCenters.data.items,
        versions: versions.data.items,
      });
    } catch (error) {
      const requestError = error instanceof ApiRequestError ? error : null;
      setState({
        kind: "error",
        message: requestError?.message ?? copy.catalogError,
        traceId: requestError?.traceId ?? null,
      });
    }
  }, []);

  useEffect(() => {
    void refresh();
    const onChange = () => {
      void refresh();
    };
    window.addEventListener("budgetlens-session", onChange);
    return () => window.removeEventListener("budgetlens-session", onChange);
  }, [refresh]);

  async function runMutation(action: () => Promise<unknown>) {
    try {
      await action();
      await refresh();
    } catch (error) {
      const requestError = error instanceof ApiRequestError ? error : null;
      setState({
        kind: "error",
        message: requestError?.message ?? copy.catalogError,
        traceId: requestError?.traceId ?? null,
      });
    }
  }

  return (
    <div className="mx-auto w-full max-w-6xl">
      <p className="text-sm font-medium text-secondary">{copy.appName}</p>
      <h1 className="mt-2 text-[28px] font-semibold leading-9 text-primary">{copy.catalogTitle}</h1>
      <p className="mt-2 max-w-3xl text-base text-secondary">{copy.catalogDescription}</p>

      {state.kind === "idle" ? (
        <section className="mt-8 rounded-surface border border-border bg-surface p-6">
          <p className="text-sm text-secondary">{copy.sessionNeeded}</p>
        </section>
      ) : null}

      {state.kind === "loading" ? (
        <section
          aria-busy="true"
          aria-label={copy.catalogLoading}
          className="mt-8 rounded-surface border border-border bg-surface p-6"
        >
          <p className="text-sm font-medium text-secondary">{copy.catalogLoading}</p>
          <div className="mt-6 space-y-3">
            <div className="h-8 animate-pulse rounded bg-[#eaecf0]" />
            <div className="h-24 animate-pulse rounded bg-[#eaecf0]" />
          </div>
        </section>
      ) : null}

      {state.kind === "error" ? (
        <section className="mt-8 rounded-surface border border-border bg-surface p-6">
          <h2 className="text-lg font-semibold text-primary">{copy.catalogError}</h2>
          <p className="mt-2 text-sm text-secondary">{state.message}</p>
          {state.traceId ? (
            <p className="mt-2 text-xs text-secondary">
              {copy.traceLabel}: {state.traceId}
            </p>
          ) : null}
          <div className="mt-4">
            <Button onClick={() => void refresh()}>{copy.retry}</Button>
          </div>
        </section>
      ) : null}

      {state.kind === "ready" ? (
        <div className="mt-8 space-y-8">
          <p className="text-sm text-secondary">
            {state.me.display_name} · {copy.roleLabel}: {personaLabel(state.me.persona)} ·{" "}
            {copy.currencyLabel} en totales de la organización
          </p>
          <CatalogTable
            title={copy.accountsTitle}
            empty={copy.emptyAccounts}
            columns={[copy.code, copy.name, copy.type, copy.status]}
            rows={state.accounts.map((item) => [
              item.code,
              item.name,
              item.account_type,
              item.status,
            ])}
          />
          {state.me.capabilities.can_manage_dimensions ? (
            <form
              className="grid gap-3 md:grid-cols-4"
              onSubmit={(event) => {
                event.preventDefault();
                const context = auth();
                if (!context) {
                  return;
                }
                void runMutation(() => createAccount(apiBaseUrl(), context, accountForm));
              }}
            >
              <input
                required
                className="h-10 rounded-control border border-border px-3 text-sm"
                placeholder={copy.code}
                value={accountForm.code}
                onChange={(event) =>
                  setAccountForm((current) => ({ ...current, code: event.target.value }))
                }
              />
              <input
                required
                className="h-10 rounded-control border border-border px-3 text-sm"
                placeholder={copy.name}
                value={accountForm.name}
                onChange={(event) =>
                  setAccountForm((current) => ({ ...current, name: event.target.value }))
                }
              />
              <select
                className="h-10 rounded-control border border-border px-3 text-sm"
                value={accountForm.account_type}
                onChange={(event) =>
                  setAccountForm((current) => ({ ...current, account_type: event.target.value }))
                }
              >
                <option value="revenue">revenue</option>
                <option value="expense">expense</option>
                <option value="asset">asset</option>
                <option value="liability">liability</option>
                <option value="equity">equity</option>
                <option value="other">other</option>
              </select>
              <Button type="submit">{copy.createAccount}</Button>
            </form>
          ) : null}

          <CatalogTable
            title={copy.departmentsTitle}
            empty={copy.emptyDepartments}
            columns={[copy.code, copy.name, copy.status]}
            rows={state.departments.map((item) => [item.code, item.name, item.status])}
          />
          {state.me.capabilities.can_manage_dimensions ? (
            <form
              className="grid gap-3 md:grid-cols-3"
              onSubmit={(event) => {
                event.preventDefault();
                const context = auth();
                if (!context) {
                  return;
                }
                void runMutation(() => createDepartment(apiBaseUrl(), context, departmentForm));
              }}
            >
              <input
                required
                className="h-10 rounded-control border border-border px-3 text-sm"
                placeholder={copy.code}
                value={departmentForm.code}
                onChange={(event) =>
                  setDepartmentForm((current) => ({ ...current, code: event.target.value }))
                }
              />
              <input
                required
                className="h-10 rounded-control border border-border px-3 text-sm"
                placeholder={copy.name}
                value={departmentForm.name}
                onChange={(event) =>
                  setDepartmentForm((current) => ({ ...current, name: event.target.value }))
                }
              />
              <Button type="submit">{copy.createDepartment}</Button>
            </form>
          ) : null}

          <CatalogTable
            title={copy.costCentersTitle}
            empty={copy.emptyCostCenters}
            columns={[copy.code, copy.name, copy.status]}
            rows={state.costCenters.map((item) => [item.code, item.name, item.status])}
          />
          {state.me.capabilities.can_manage_dimensions ? (
            <form
              className="grid gap-3 md:grid-cols-3"
              onSubmit={(event) => {
                event.preventDefault();
                const context = auth();
                if (!context) {
                  return;
                }
                void runMutation(() => createCostCenter(apiBaseUrl(), context, costCenterForm));
              }}
            >
              <input
                required
                className="h-10 rounded-control border border-border px-3 text-sm"
                placeholder={copy.code}
                value={costCenterForm.code}
                onChange={(event) =>
                  setCostCenterForm((current) => ({ ...current, code: event.target.value }))
                }
              />
              <input
                required
                className="h-10 rounded-control border border-border px-3 text-sm"
                placeholder={copy.name}
                value={costCenterForm.name}
                onChange={(event) =>
                  setCostCenterForm((current) => ({ ...current, name: event.target.value }))
                }
              />
              <Button type="submit">{copy.createCostCenter}</Button>
            </form>
          ) : null}

          <section>
            <h2 className="text-lg font-semibold text-primary">{copy.versionsTitle}</h2>
            {state.versions.length === 0 ? (
              <p className="mt-3 text-sm text-secondary">{copy.emptyVersions}</p>
            ) : (
              <ul className="mt-3 space-y-3">
                {state.versions.map((version) => (
                  <li
                    key={version.id}
                    className="rounded-surface border border-border bg-surface p-4"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-medium text-primary">{version.name}</p>
                        <p className="text-sm text-secondary">
                          {copy.fiscalYear} {version.fiscal_year} · {version.status}
                          {version.is_active ? ` · ${copy.active}` : ""}
                        </p>
                      </div>
                      {state.me.capabilities.can_manage_versions ? (
                        <div className="flex flex-wrap gap-2">
                          {version.status === "draft" ? (
                            <Button
                              variant="secondary"
                              onClick={() => {
                                if (!window.confirm(copy.confirmPublish)) {
                                  return;
                                }
                                const context = auth();
                                if (!context) {
                                  return;
                                }
                                void runMutation(() =>
                                  publishBudgetVersion(apiBaseUrl(), context, version.id),
                                );
                              }}
                            >
                              {copy.publish}
                            </Button>
                          ) : null}
                          {version.status === "published" && !version.is_active ? (
                            <Button
                              variant="secondary"
                              onClick={() => {
                                if (!window.confirm(copy.confirmActivate)) {
                                  return;
                                }
                                const context = auth();
                                if (!context) {
                                  return;
                                }
                                void runMutation(() =>
                                  activateBudgetVersion(apiBaseUrl(), context, version.id),
                                );
                              }}
                            >
                              {copy.activate}
                            </Button>
                          ) : null}
                          {version.status !== "archived" ? (
                            <Button
                              variant="ghost"
                              onClick={() => {
                                if (!window.confirm(copy.confirmArchive)) {
                                  return;
                                }
                                const context = auth();
                                if (!context) {
                                  return;
                                }
                                void runMutation(() =>
                                  archiveBudgetVersion(apiBaseUrl(), context, version.id),
                                );
                              }}
                            >
                              {copy.archive}
                            </Button>
                          ) : null}
                        </div>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>

          {state.me.capabilities.can_manage_versions ? (
            <form
              className="grid gap-3 md:grid-cols-3"
              onSubmit={(event) => {
                event.preventDefault();
                const context = auth();
                if (!context) {
                  return;
                }
                void runMutation(() =>
                  createBudgetVersion(apiBaseUrl(), context, {
                    name: versionForm.name,
                    fiscal_year: Number(versionForm.fiscal_year),
                  }),
                );
              }}
            >
              <input
                required
                className="h-10 rounded-control border border-border px-3 text-sm"
                placeholder={copy.name}
                value={versionForm.name}
                onChange={(event) =>
                  setVersionForm((current) => ({ ...current, name: event.target.value }))
                }
              />
              <input
                required
                className="h-10 rounded-control border border-border px-3 text-sm"
                placeholder={copy.fiscalYear}
                value={versionForm.fiscal_year}
                onChange={(event) =>
                  setVersionForm((current) => ({ ...current, fiscal_year: event.target.value }))
                }
              />
              <Button type="submit">{copy.createVersion}</Button>
            </form>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function CatalogTable({
  title,
  empty,
  columns,
  rows,
}: {
  title: string;
  empty: string;
  columns: string[];
  rows: string[][];
}) {
  return (
    <section className="rounded-surface border border-border bg-surface p-6">
      <h2 className="text-lg font-semibold text-primary">{title}</h2>
      {rows.length === 0 ? (
        <p className="mt-3 text-sm text-secondary">{empty}</p>
      ) : (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[520px] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-secondary">
                {columns.map((column) => (
                  <th key={column} className="py-2 font-medium">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.join("-")} className="border-b border-border last:border-0">
                  {row.map((cell) => (
                    <td key={cell} className="py-2 text-primary">
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
