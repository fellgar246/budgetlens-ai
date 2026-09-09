"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

import { copy } from "@/lib/copy";

const REASONS: Record<string, string> = {
  missing_code: copy.authErrorMissingCode,
  state_mismatch: copy.authErrorState,
  token_exchange: copy.authErrorToken,
  missing_config: copy.authErrorConfig,
  unauthenticated: copy.authErrorGeneric,
};

export function AuthErrorPage() {
  const [detail, setDetail] = useState<string>(copy.authErrorGeneric);

  useEffect(() => {
    const reason = new URLSearchParams(window.location.search).get("reason") ?? "";
    setDetail(REASONS[reason] ?? copy.authErrorGeneric);
  }, []);

  return (
    <section className="rounded-surface border border-border bg-surface p-6">
      <h1 className="text-[28px] font-semibold leading-9 text-primary">{copy.authErrorTitle}</h1>
      <p className="mt-2 text-base text-secondary">{detail}</p>
      <p className="mt-2 text-sm text-secondary">{copy.errorCorrective}</p>
      <Link
        className="mt-6 inline-flex h-10 items-center text-sm font-medium text-brand-600"
        href="/login/"
      >
        {copy.authRetry}
      </Link>
    </section>
  );
}
