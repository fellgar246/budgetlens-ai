"use client";

import { useCallback, useEffect, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import {
  type AnalysisFilters,
  EMPTY_ANALYSIS_FILTERS,
  parseAnalysisFilters,
  serializeAnalysisFilters,
  writeStoredFilters,
} from "@/lib/analysis-filters";

import { useSession } from "./SessionProvider";

export function useAnalysisFilters() {
  const { organizationId } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const search = searchParams.toString();

  const filters = useMemo(() => parseAnalysisFilters(search), [search]);

  useEffect(() => {
    if (organizationId) {
      writeStoredFilters(organizationId, filters);
    }
  }, [filters, organizationId]);

  const replaceFilters = useCallback(
    (next: AnalysisFilters) => {
      const query = serializeAnalysisFilters(next);
      router.replace(query ? `${pathname}?${query}` : pathname);
    },
    [pathname, router],
  );

  const update = useCallback(
    (patch: Partial<AnalysisFilters>) => {
      replaceFilters({ ...filters, ...patch });
    },
    [filters, replaceFilters],
  );

  const reset = useCallback(() => {
    replaceFilters(EMPTY_ANALYSIS_FILTERS);
  }, [replaceFilters]);

  return { filters, update, reset };
}
