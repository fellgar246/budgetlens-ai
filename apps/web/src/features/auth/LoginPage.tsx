"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";

export function LoginPage() {
  const router = useRouter();
  const { authMode, users, userId, setUserId, beginLogin } = useSession();
  const [signedOut, setSignedOut] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSignedOut(new URLSearchParams(window.location.search).get("signed_out") === "1");
  }, []);

  if (authMode === "oidc") {
    return (
      <section className="rounded-surface border border-border bg-surface p-6">
        <h1 className="text-[28px] font-semibold leading-9 text-primary">{copy.loginTitle}</h1>
        <p className="mt-2 text-base text-secondary">{copy.oidcLoginDescription}</p>
        {signedOut ? (
          <p className="mt-4 text-sm text-primary" role="status">
            {copy.signedOutDetail}
          </p>
        ) : null}
        {error ? (
          <p className="mt-4 text-sm text-danger" role="alert">
            {error}
          </p>
        ) : null}
        <Button
          className="mt-6 w-full"
          loading={busy}
          onClick={() => {
            setBusy(true);
            void beginLogin().catch(() => {
              setBusy(false);
              setError(copy.authErrorConfig);
            });
          }}
        >
          {copy.continueWithIdentity}
        </Button>
      </section>
    );
  }

  return (
    <section className="rounded-surface border border-border bg-surface p-6">
      <h1 className="text-[28px] font-semibold leading-9 text-primary">{copy.loginTitle}</h1>
      <p className="mt-2 text-base text-secondary">{copy.loginDescription}</p>
      {signedOut ? (
        <p className="mt-4 text-sm text-primary" role="status">
          {copy.signedOutDetail}
        </p>
      ) : null}
      <div className="mt-6">
        <Select
          label={copy.selectUser}
          value={userId}
          onChange={(event) => setUserId(event.target.value)}
        >
          <option value="">{copy.chooseUser}</option>
          {users.map((user) => (
            <option key={user.id} value={user.id}>
              {user.display_name} · {user.email}
            </option>
          ))}
        </Select>
      </div>
      <Button
        className="mt-2"
        disabled={!userId}
        onClick={() => router.push("/select-organization/")}
      >
        {copy.continueToOrganization}
      </Button>
    </section>
  );
}
