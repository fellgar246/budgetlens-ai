"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import type { BudgetVersion } from "@budgetlens/api-client";

import {
  type AnalysisFilters,
  EMPTY_ANALYSIS_FILTERS,
  hasMeaningfulFilters,
  normalizeAnalysisHref,
  resolveAnalysisFilters,
  serializeAnalysisFilters,
  withDefaultVersion,
  withTrailingSlash,
  writeStoredFilters,
} from "@/lib/analysis-filters";

import { useSession } from "./SessionProvider";

const NO_VERSIONS: BudgetVersion[] = [];

function normalizePath(value: string | null | undefined): string {
  return (value ?? "/").replace(/\/$/, "") || "/";
}

function windowPathname(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return normalizePath(window.location.pathname);
}

function windowHref(): string {
  if (typeof window === "undefined") {
    return "";
  }
  return `${window.location.pathname}${window.location.search}`;
}

export function useAnalysisFilters(versions: BudgetVersion[] = NO_VERSIONS) {
  const { organizationId } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const search = searchParams.toString();
  const [optimistic, setOptimistic] = useState<AnalysisFilters | null>(null);

  const urlFilters = useMemo(
    () => resolveAnalysisFilters(search, organizationId, versions),
    [organizationId, search, versions],
  );
  const filters = optimistic ?? urlFilters;

  const hrefFor = useCallback(
    (next: AnalysisFilters) => {
      const query = serializeAnalysisFilters(next);
      const path = withTrailingSlash(pathname);
      return query ? `${path}?${query}` : path;
    },
    [pathname],
  );

  const writeUrl = useCallback(
    (next: AnalysisFilters, history: "replace" | "push") => {
      if (typeof window === "undefined") {
        return;
      }
      if (normalizePath(pathname) !== windowPathname()) {
        return;
      }
      const href = hrefFor(next);
      if (normalizeAnalysisHref(href) === normalizeAnalysisHref(windowHref())) {
        return;
      }
      if (history === "push") {
        router.push(href);
        return;
      }
      window.history.replaceState(window.history.state ?? {}, "", href);
    },
    [hrefFor, pathname, router],
  );

  useEffect(() => {
    if (!optimistic) {
      return;
    }
    if (serializeAnalysisFilters(optimistic) === serializeAnalysisFilters(urlFilters)) {
      setOptimistic(null);
    }
  }, [optimistic, urlFilters]);

  useEffect(() => {
    setOptimistic(null);
  }, [organizationId, pathname]);

  useEffect(() => {
    if (organizationId && hasMeaningfulFilters(filters)) {
      writeStoredFilters(organizationId, filters);
    }
  }, [filters, organizationId]);

  useEffect(() => {
    if (!organizationId || optimistic) {
      return;
    }
    if (normalizePath(pathname) !== windowPathname()) {
      return;
    }
    const href = hrefFor(urlFilters);
    const fromSearch = search ? `${pathname}?${search}` : pathname;
    if (normalizeAnalysisHref(href) === normalizeAnalysisHref(fromSearch)) {
      return;
    }
    if (normalizeAnalysisHref(href) === normalizeAnalysisHref(windowHref())) {
      return;
    }
    writeUrl(urlFilters, "replace");
  }, [hrefFor, optimistic, organizationId, pathname, search, urlFilters, writeUrl]);

  const update = useCallback(
    (patch: Partial<AnalysisFilters>, history: "replace" | "push" = "replace") => {
      const next = withDefaultVersion({ ...filters, ...patch }, versions);
      if (!("cursor" in patch)) {
        next.cursor = "";
      }
      if (organizationId) {
        writeStoredFilters(organizationId, next);
      }
      setOptimistic(next);
      writeUrl(next, history);
    },
    [filters, organizationId, versions, writeUrl],
  );

  const reset = useCallback(() => {
    const next = withDefaultVersion(EMPTY_ANALYSIS_FILTERS, versions);
    if (organizationId) {
      writeStoredFilters(organizationId, next);
    }
    setOptimistic(next);
    writeUrl(next, "replace");
  }, [organizationId, versions, writeUrl]);

  return { filters, update, reset };
}
