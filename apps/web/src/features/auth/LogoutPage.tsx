"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useSession } from "@/features/session/SessionProvider";
import { copy } from "@/lib/copy";

export function LogoutPage() {
  const router = useRouter();
  const { signOut, authMode } = useSession();

  useEffect(() => {
    void signOut().finally(() => {
      if (authMode !== "oidc") {
        router.replace("/login/?signed_out=1");
      }
    });
  }, [authMode, router, signOut]);

  return (
    <section className="rounded-surface border border-border bg-surface p-6">
      <h1 className="text-[28px] font-semibold leading-9 text-primary">{copy.signedOutTitle}</h1>
      <p className="mt-2 text-base text-secondary">{copy.signedOutDetail}</p>
    </section>
  );
}
