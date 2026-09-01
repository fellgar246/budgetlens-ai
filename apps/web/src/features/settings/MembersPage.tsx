"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ApiRequestError,
  createMembership,
  listMemberships,
  type Membership,
} from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { EmptyState } from "@/components/layout/EmptyState";
import { PageHeader } from "@/components/layout/PageHeader";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";

export function MembersPage() {
  const { userId, organizationId, users, capabilities, generation } = useSession();
  const [members, setMembers] = useState<Membership[]>([]);
  const [userToAdd, setUserToAdd] = useState("");
  const [role, setRole] = useState<"viewer" | "analyst" | "admin">("viewer");
  const [error, setError] = useState<string | null>(null);
  const hasSession = Boolean(userId && organizationId);

  const refresh = useCallback(async () => {
    if (!userId || !organizationId) {
      setMembers([]);
      return;
    }
    try {
      const result = await listMemberships(apiBaseUrl(), sessionAuth(userId, organizationId));
      setMembers(result.data.items);
      setError(null);
    } catch (err) {
      setMembers([]);
      setError(err instanceof ApiRequestError ? err.message : copy.catalogError);
    }
  }, [organizationId, userId]);

  useEffect(() => {
    void refresh();
  }, [generation, refresh]);

  return (
    <CapabilityGate allowed={capabilities.can_manage_members} hasSession={hasSession}>
      <PageHeader title={copy.membersTitle} description={copy.membersDescription} />
      {error ? <p className="mt-4 text-sm text-danger">{error}</p> : null}
      {members.length === 0 ? (
        <EmptyState title={copy.emptyMembers} detail={copy.membersDescription} />
      ) : (
        <table className="mt-8 w-full min-w-[480px] text-left text-sm">
          <thead>
            <tr className="border-b border-border text-secondary">
              <th className="py-2 font-medium">{copy.selectUser}</th>
              <th className="py-2 font-medium">{copy.roleLabel}</th>
              <th className="py-2 font-medium">{copy.status}</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.id} className="border-b border-border">
                <td className="py-2">
                  {users.find((user) => user.id === member.user_id)?.display_name ?? member.user_id}
                </td>
                <td className="py-2">{member.role}</td>
                <td className="py-2">{member.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form
        className="mt-8 grid gap-3 md:grid-cols-3"
        onSubmit={(event) => {
          event.preventDefault();
          if (!userId || !organizationId || !userToAdd) {
            return;
          }
          void createMembership(apiBaseUrl(), sessionAuth(userId, organizationId), {
            user_id: userToAdd,
            role,
          })
            .then(() => refresh())
            .catch((err: Error) => setError(err.message));
        }}
      >
        <select
          className="h-10 rounded-control border border-border px-3 text-sm"
          value={userToAdd}
          onChange={(event) => setUserToAdd(event.target.value)}
        >
          <option value="">{copy.chooseUser}</option>
          {users.map((user) => (
            <option key={user.id} value={user.id}>
              {user.display_name}
            </option>
          ))}
        </select>
        <select
          className="h-10 rounded-control border border-border px-3 text-sm"
          value={role}
          onChange={(event) => setRole(event.target.value as "viewer" | "analyst" | "admin")}
        >
          <option value="viewer">viewer</option>
          <option value="analyst">analyst</option>
          <option value="admin">admin</option>
        </select>
        <Button type="submit">{copy.addMember}</Button>
      </form>
    </CapabilityGate>
  );
}
