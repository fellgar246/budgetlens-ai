export type GroupByDimension = "department" | "account" | "cost_center";

export type AnalysisFilters = {
  budgetVersionId: string;
  periodFrom: string;
  periodTo: string;
  departmentId: string;
  accountId: string;
  costCenterId: string;
  sort: "unfavorable" | "variance_amount";
  groupBy: GroupByDimension;
  cursor: string;
};

export const EMPTY_ANALYSIS_FILTERS: AnalysisFilters = {
  budgetVersionId: "",
  periodFrom: "",
  periodTo: "",
  departmentId: "",
  accountId: "",
  costCenterId: "",
  sort: "unfavorable",
  groupBy: "department",
  cursor: "",
};

const FILTER_PREFIX = "budgetlens.filters.";

export function parseAnalysisFilters(search: string): AnalysisFilters {
  const params = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);
  const sort = params.get("sort");
  const groupBy = params.get("group_by");
  return {
    budgetVersionId: params.get("version") ?? "",
    periodFrom: params.get("period_from") ?? "",
    periodTo: params.get("period_to") ?? "",
    departmentId: params.get("department") ?? "",
    accountId: params.get("account") ?? "",
    costCenterId: params.get("cost_center") ?? "",
    sort: sort === "variance_amount" ? "variance_amount" : "unfavorable",
    groupBy:
      groupBy === "account" || groupBy === "cost_center" || groupBy === "department"
        ? groupBy
        : "department",
    cursor: params.get("cursor") ?? "",
  };
}

export function serializeAnalysisFilters(filters: AnalysisFilters): string {
  const params = new URLSearchParams();
  if (filters.budgetVersionId) {
    params.set("version", filters.budgetVersionId);
  }
  if (filters.periodFrom) {
    params.set("period_from", filters.periodFrom);
  }
  if (filters.periodTo) {
    params.set("period_to", filters.periodTo);
  }
  if (filters.departmentId) {
    params.set("department", filters.departmentId);
  }
  if (filters.accountId) {
    params.set("account", filters.accountId);
  }
  if (filters.costCenterId) {
    params.set("cost_center", filters.costCenterId);
  }
  if (filters.sort !== "unfavorable") {
    params.set("sort", filters.sort);
  }
  if (filters.groupBy && filters.groupBy !== "department") {
    params.set("group_by", filters.groupBy);
  }
  if (filters.cursor) {
    params.set("cursor", filters.cursor);
  }
  return params.toString();
}

export function filtersStorageKey(organizationId: string): string {
  return `${FILTER_PREFIX}${organizationId}`;
}

export function readStoredFilters(organizationId: string | null): AnalysisFilters {
  if (!organizationId || typeof window === "undefined") {
    return EMPTY_ANALYSIS_FILTERS;
  }
  const raw = window.sessionStorage.getItem(filtersStorageKey(organizationId));
  if (!raw) {
    return EMPTY_ANALYSIS_FILTERS;
  }
  try {
    return { ...EMPTY_ANALYSIS_FILTERS, ...(JSON.parse(raw) as AnalysisFilters) };
  } catch {
    return EMPTY_ANALYSIS_FILTERS;
  }
}

export function writeStoredFilters(organizationId: string, filters: AnalysisFilters): void {
  if (typeof window === "undefined") {
    return;
  }
  window.sessionStorage.setItem(filtersStorageKey(organizationId), JSON.stringify(filters));
}

export function clearStoredFilters(organizationId: string | null): void {
  if (!organizationId || typeof window === "undefined") {
    return;
  }
  window.sessionStorage.removeItem(filtersStorageKey(organizationId));
}

export function withPathFilters(pathname: string, filters: AnalysisFilters): string {
  const query = serializeAnalysisFilters(filters);
  return query ? `${pathname}?${query}` : pathname;
}
