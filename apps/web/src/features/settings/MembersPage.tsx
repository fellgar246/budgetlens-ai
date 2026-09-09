"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ApiRequestError,
  createMembership,
  listMemberships,
  patchMembership,
  type Membership,
} from "@budgetlens/api-client";

import { Button } from "@/components/ui/Button";
import { Dialog } from "@/components/ui/Dialog";
import { ErrorBanner } from "@/components/ui/ErrorBanner";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { CapabilityGate } from "@/components/layout/CapabilityGate";
import { EmptyState } from "@/components/layout/EmptyState";
import { PageHeader } from "@/components/layout/PageHeader";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";
import { memberRoleLabel, memberStatusLabel } from "@/lib/labels";
import { apiBaseUrl } from "@/lib/env";
import { sessionAuth } from "@/lib/session-auth";

export function MembersPage() {
  const { userId, organizationId, users, capabilities, generation, authMode } = useSession();
  const [members, setMembers] = useState<Membership[]>([]);
  const [userToAdd, setUserToAdd] = useState("");
  const [role, setRole] = useState<"viewer" | "analyst" | "admin">("viewer");
  const [error, setError] = useState<Error | string | null>(null);
  const [pendingDisable, setPendingDisable] = useState<Membership | null>(null);
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
      setError(err instanceof ApiRequestError ? err : copy.catalogError);
    }
  }, [organizationId, userId]);

  useEffect(() => {
    void refresh();
  }, [generation, refresh]);

  function memberLabel(member: Membership): string {
    const local = users.find((user) => user.id === member.user_id);
    return local?.email ?? local?.display_name ?? member.user_id;
  }

  return (
    <CapabilityGate allowed={capabilities.can_manage_members} hasSession={hasSession}>
      <PageHeader title={copy.membersTitle} description={copy.membersDescription} />
      <ErrorBanner error={error} onRetry={() => void refresh()} />
      {members.length === 0 ? (
        <EmptyState title={copy.emptyMembers} detail={copy.membersDescription} />
      ) : (
        <table className="mt-8 w-full min-w-[480px] text-left text-sm">
          <thead>
            <tr className="border-b border-border text-secondary">
              <th className="py-2 font-medium">{copy.emailLabel}</th>
              <th className="py-2 font-medium">{copy.roleLabel}</th>
              <th className="py-2 font-medium">{copy.status}</th>
              <th className="py-2 font-medium">{copy.changeRole}</th>
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <tr key={member.id} className="border-b border-border">
                <td className="py-2">{memberLabel(member)}</td>
                <td className="py-2">{memberRoleLabel(member.role)}</td>
                <td className="py-2">{memberStatusLabel(member.status)}</td>
                <td className="py-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <Select
                      label={copy.roleLabel}
                      className="min-w-36"
                      value={member.role}
                      onChange={(event) => {
                        void patchMembership(
                          apiBaseUrl(),
                          sessionAuth(userId, organizationId),
                          member.id,
                          { role: event.target.value as "viewer" | "analyst" | "admin" },
                        )
                          .then(() => refresh())
                          .catch((err: Error) => setError(err));
                      }}
                    >
                      <option value="viewer">{copy.roleViewer}</option>
                      <option value="analyst">{copy.roleAnalyst}</option>
                      <option value="admin">{copy.roleAdmin}</option>
                    </Select>
                    {member.status === "disabled" ? (
                      <Button
                        variant="secondary"
                        onClick={() => {
                          void patchMembership(
                            apiBaseUrl(),
                            sessionAuth(userId, organizationId),
                            member.id,
                            { status: "active" },
                          )
                            .then(() => refresh())
                            .catch((err: Error) => setError(err));
                        }}
                      >
                        {copy.enableMember}
                      </Button>
                    ) : (
                      <Button variant="danger" onClick={() => setPendingDisable(member)}>
                        {copy.disableMember}
                      </Button>
                    )}
                  </div>
                </td>
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
            .then(() => {
              setUserToAdd("");
              return refresh();
            })
            .catch((err: Error) => setError(err));
        }}
      >
        {authMode === "dev" && users.length > 0 ? (
          <Select
            label={copy.selectUser}
            value={userToAdd}
            onChange={(event) => setUserToAdd(event.target.value)}
          >
            <option value="">{copy.chooseUser}</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.display_name}
              </option>
            ))}
          </Select>
        ) : (
          <Input
            label={copy.memberUserId}
            hint={copy.memberUserIdHint}
            value={userToAdd}
            onChange={(event) => setUserToAdd(event.target.value)}
          />
        )}
        <Select
          label={copy.roleLabel}
          value={role}
          onChange={(event) => setRole(event.target.value as "viewer" | "analyst" | "admin")}
        >
          <option value="viewer">{copy.roleViewer}</option>
          <option value="analyst">{copy.roleAnalyst}</option>
          <option value="admin">{copy.roleAdmin}</option>
        </Select>
        <Button type="submit">{copy.addMember}</Button>
      </form>
      <Dialog
        open={pendingDisable !== null}
        title={copy.disableMember}
        onClose={() => setPendingDisable(null)}
        footer={
          <>
            <Button variant="secondary" onClick={() => setPendingDisable(null)}>
              {copy.close}
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                if (!pendingDisable || !userId || !organizationId) {
                  return;
                }
                void patchMembership(
                  apiBaseUrl(),
                  sessionAuth(userId, organizationId),
                  pendingDisable.id,
                  { status: "disabled" },
                )
                  .then(() => {
                    setPendingDisable(null);
                    return refresh();
                  })
                  .catch((err: Error) => setError(err));
              }}
            >
              {copy.confirmDisableMemberAction}
            </Button>
          </>
        }
      >
        <p className="text-sm text-secondary">{copy.confirmDisableMember}</p>
        {pendingDisable ? (
          <p className="mt-2 text-sm text-primary">{memberLabel(pendingDisable)}</p>
        ) : null}
      </Dialog>
    </CapabilityGate>
  );
}
