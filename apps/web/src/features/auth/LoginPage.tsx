"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";

export function LoginPage() {
  const router = useRouter();
  const { users, userId, setUserId } = useSession();

  return (
    <section className="rounded-surface border border-border bg-surface p-6">
      <h1 className="text-[28px] font-semibold leading-9 text-primary">{copy.loginTitle}</h1>
      <p className="mt-2 text-base text-secondary">{copy.loginDescription}</p>
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
