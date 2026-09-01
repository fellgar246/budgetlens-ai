"use client";

import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/Button";
import { Select } from "@/components/ui/Select";
import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";

export function SelectOrganizationPage() {
  const router = useRouter();
  const { organizations, organizationId, userId, setOrganizationId } = useSession();

  return (
    <section className="rounded-surface border border-border bg-surface p-6">
      <h1 className="text-[28px] font-semibold leading-9 text-primary">
        {copy.selectOrganizationTitle}
      </h1>
      <p className="mt-2 text-base text-secondary">{copy.selectOrganizationDescription}</p>
      <div className="mt-6">
        <Select
          label={copy.selectOrganization}
          value={organizationId}
          disabled={!userId}
          onChange={(event) => setOrganizationId(event.target.value)}
        >
          <option value="">
            {userId && organizations.length === 0 ? copy.noOrganizations : copy.chooseOrganization}
          </option>
          {organizations.map((organization) => (
            <option key={organization.id} value={organization.id}>
              {organization.name} · {organization.role} · {organization.functional_currency}
            </option>
          ))}
        </Select>
      </div>
      <Button
        className="mt-2"
        disabled={!organizationId}
        onClick={() => router.push("/dashboard/")}
      >
        {copy.enterWorkspace}
      </Button>
    </section>
  );
}
