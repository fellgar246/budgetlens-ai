"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { useAuth } from "@/features/auth/AuthProvider";
import { OidcError } from "@/features/auth/oidc";
import { copy } from "@/lib/copy";

export function CallbackPage() {
  const router = useRouter();
  const { completeCallback } = useAuth();
  const [status, setStatus] = useState<string>(copy.authCallbackDetail);

  useEffect(() => {
    const current = new URL(window.location.href);
    void completeCallback(current)
      .then(() => {
        router.replace("/select-organization/");
      })
      .catch((error: unknown) => {
        const reason = error instanceof OidcError ? error.reason : "token_exchange";
        setStatus(copy.authErrorGeneric);
        router.replace(`/auth/error/?reason=${encodeURIComponent(reason)}`);
      });
  }, [completeCallback, router]);

  return (
    <section className="rounded-surface border border-border bg-surface p-6">
      <h1 className="text-[28px] font-semibold leading-9 text-primary">{copy.authCallbackTitle}</h1>
      <p className="mt-2 text-base text-secondary" aria-live="polite">
        {status}
      </p>
    </section>
  );
}
