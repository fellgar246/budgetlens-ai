export const API_PREFIX = "/api/v1";

export type LiveStatusResponse = {
  status: "ok";
};

export type ReadyStatusResponse = {
  status: "ready" | "unavailable";
  components: {
    database: "ok" | "error";
  };
};

export type VersionResponse = {
  version: string;
  commit: string;
  build_time: string;
};

export type ApiErrorEnvelope = {
  error: {
    code: string;
    message: string;
    field_errors: Array<{ field?: string; code: string; message: string }>;
    retryable: boolean;
  };
  trace_id: string;
};

export type PageInfo = {
  next_cursor: string | null;
  has_more: boolean;
};

export type Organization = {
  id: string;
  name: string;
  slug: string;
  functional_currency: string;
  fiscal_year_start_month: number;
  status: string;
  role: string | null;
  version: number;
  conversation_retention_days: number;
  created_at: string;
  updated_at: string;
};

export type Capabilities = {
  can_view_dashboard: boolean;
  can_import: boolean;
  can_publish_budget: boolean;
  can_create_scenario: boolean;
  can_use_copilot: boolean;
  can_manage_members: boolean;
  can_view_technical_metrics: boolean;
  can_deploy_rollback: boolean;
  can_export: boolean;
  can_manage_versions: boolean;
  can_manage_dimensions: boolean;
  can_manage_organization: boolean;
};

export type MeResponse = {
  id: string;
  email: string;
  display_name: string;
  status: string;
  auth_mode: string;
  role: string | null;
  persona: string | null;
  capabilities: Capabilities;
};

export type Account = {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  account_type: string;
  parent_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Department = {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type CostCenter = {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type BudgetVersion = {
  id: string;
  organization_id: string;
  name: string;
  fiscal_year: number;
  status: string;
  is_active: boolean;
  published_at: string | null;
  published_by: string | null;
  created_at: string;
  version: number;
};

export type DevIdentity = {
  id: string;
  email: string;
  display_name: string;
  platform_role: string | null;
  memberships: Array<{
    organization_id: string;
    organization_name: string;
    role: string;
  }>;
};

export type Membership = {
  id: string;
  organization_id: string;
  user_id: string;
  role: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type Paginated<T> = {
  items: T[];
  page: PageInfo;
};

export class ApiRequestError extends Error {
  readonly status: number;
  readonly traceId: string | null;
  readonly code: string | null;

  constructor(message: string, status: number, traceId: string | null, code: string | null = null) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.traceId = traceId;
    this.code = code;
  }
}

export type AuthContext = {
  token: string;
  organizationId?: string;
  idempotencyKey?: string;
};

export function apiUrl(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

function readTraceId(response: Response): string | null {
  return response.headers.get("X-Trace-Id") ?? response.headers.get("x-trace-id");
}

async function sendJson<T>(
  baseUrl: string,
  path: string,
  init: RequestInit = {},
  auth?: AuthContext,
): Promise<{ data: T; traceId: string | null; status: number }> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body) {
    headers.set("Content-Type", "application/json");
  }
  if (auth?.token) {
    headers.set("Authorization", `Bearer ${auth.token}`);
  }
  if (auth?.organizationId) {
    headers.set("X-Organization-Id", auth.organizationId);
  }
  if (auth?.idempotencyKey) {
    headers.set("Idempotency-Key", auth.idempotencyKey);
  }

  let response: Response;
  try {
    response = await fetch(apiUrl(baseUrl, path), { ...init, headers });
  } catch {
    throw new ApiRequestError("No se pudo contactar la API.", 0, null);
  }

  const traceId = readTraceId(response);
  const data = (await response.json()) as T;
  return { data, traceId, status: response.status };
}

async function requestJson<T>(
  baseUrl: string,
  path: string,
  init: RequestInit = {},
  auth?: AuthContext,
): Promise<{ data: T; traceId: string | null; status: number }> {
  const result = await sendJson<T | ApiErrorEnvelope>(baseUrl, path, init, auth);
  if (result.status >= 400) {
    const envelope = result.data as ApiErrorEnvelope;
    throw new ApiRequestError(
      envelope.error?.message ?? "La solicitud no se pudo completar.",
      result.status,
      envelope.trace_id ?? result.traceId,
      envelope.error?.code ?? null,
    );
  }
  return { data: result.data as T, traceId: result.traceId, status: result.status };
}

export function getLive(baseUrl: string) {
  return sendJson<LiveStatusResponse>(baseUrl, `${API_PREFIX}/health/live`);
}

export function getReady(baseUrl: string) {
  return sendJson<ReadyStatusResponse>(baseUrl, `${API_PREFIX}/health/ready`);
}

export function getVersion(baseUrl: string) {
  return sendJson<VersionResponse>(baseUrl, `${API_PREFIX}/version`);
}

export type OpsMetrics = {
  requests: Array<{
    method: string;
    route: string;
    status_class: string;
    count: number;
    errors: number;
    duration_ms_p95: number | null;
  }>;
  active_requests: number;
  db_pool: { checked_out: number; overflow: number; size: number };
  db_rollbacks: number;
  jobs: { timed_out: number; by_status: Record<string, number> };
  ai: {
    runs: number;
    tool_calls: number;
    tool_failures: number;
    latency_ms_p95: number | null;
    estimated_cost: { currency: string; amount: string; estimate: boolean } | null;
  };
  rate_limited: number;
  cost_estimate_configured: boolean;
};

export function getOpsMetrics(baseUrl: string, auth: AuthContext) {
  return requestJson<OpsMetrics>(baseUrl, `${API_PREFIX}/ops/metrics`, {}, auth);
}

export function getDevIdentities(baseUrl: string) {
  return requestJson<{ users: DevIdentity[] }>(baseUrl, `${API_PREFIX}/dev/identities`);
}

export function getMe(baseUrl: string, auth: AuthContext) {
  return requestJson<MeResponse>(baseUrl, `${API_PREFIX}/me`, {}, auth);
}

export function listOrganizations(baseUrl: string, auth: AuthContext, query?: PageQuery) {
  return requestJson<Paginated<Organization>>(
    baseUrl,
    `${API_PREFIX}/organizations` + queryString({ cursor: query?.cursor, limit: query?.limit }),
    {},
    auth,
  );
}

export function createOrganization(
  baseUrl: string,
  auth: AuthContext,
  body: {
    name: string;
    slug: string;
    functional_currency: string;
    fiscal_year_start_month: number;
  },
) {
  return requestJson<Organization>(
    baseUrl,
    `${API_PREFIX}/organizations`,
    { method: "POST", body: JSON.stringify(body) },
    auth,
  );
}

export function getOrganization(baseUrl: string, auth: AuthContext, organizationId: string) {
  return requestJson<Organization>(baseUrl, `${API_PREFIX}/organizations/${organizationId}`, {}, auth);
}

export function patchOrganization(
  baseUrl: string,
  auth: AuthContext,
  organizationId: string,
  body: {
    version: number;
    name?: string | null;
    fiscal_year_start_month?: number | null;
    status?: "active" | "archived" | null;
    conversation_retention_days?: number | null;
  },
) {
  return requestJson<Organization>(
    baseUrl,
    `${API_PREFIX}/organizations/${organizationId}`,
    { method: "PATCH", body: JSON.stringify(body) },
    auth,
  );
}

export function listMemberships(baseUrl: string, auth: AuthContext, query?: PageQuery) {
  return requestJson<Paginated<Membership>>(
    baseUrl,
    `${API_PREFIX}/memberships` + queryString({ cursor: query?.cursor, limit: query?.limit }),
    {},
    auth,
  );
}

export function createMembership(
  baseUrl: string,
  auth: AuthContext,
  body: { user_id: string; role: "viewer" | "analyst" | "admin" },
) {
  return requestJson<Membership>(
    baseUrl,
    `${API_PREFIX}/memberships`,
    { method: "POST", body: JSON.stringify(body) },
    auth,
  );
}

export function patchMembership(
  baseUrl: string,
  auth: AuthContext,
  membershipId: string,
  body: { role?: "viewer" | "analyst" | "admin" | null; status?: "active" | "disabled" | null },
) {
  return requestJson<Membership>(
    baseUrl,
    `${API_PREFIX}/memberships/${membershipId}`,
    { method: "PATCH", body: JSON.stringify(body) },
    auth,
  );
}

export function listAccounts(baseUrl: string, auth: AuthContext, query?: CatalogListQuery) {
  return requestJson<Paginated<Account>>(
    baseUrl,
    `${API_PREFIX}/accounts` +
      queryString({
        status: query?.status,
        search: query?.search,
        cursor: query?.cursor,
        limit: query?.limit,
      }),
    {},
    auth,
  );
}

export function createAccount(
  baseUrl: string,
  auth: AuthContext,
  body: { code: string; name: string; account_type: string },
) {
  return requestJson<Account>(baseUrl, `${API_PREFIX}/accounts`, { method: "POST", body: JSON.stringify(body) }, auth);
}

export function getAccount(baseUrl: string, auth: AuthContext, accountId: string) {
  return requestJson<Account>(baseUrl, `${API_PREFIX}/accounts/${accountId}`, {}, auth);
}

export function patchAccount(
  baseUrl: string,
  auth: AuthContext,
  accountId: string,
  body: {
    name?: string | null;
    account_type?: string | null;
    parent_id?: string | null;
    clear_parent?: boolean;
    status?: "active" | "inactive" | null;
  },
) {
  return requestJson<Account>(
    baseUrl,
    `${API_PREFIX}/accounts/${accountId}`,
    { method: "PATCH", body: JSON.stringify(body) },
    auth,
  );
}

export function listDepartments(baseUrl: string, auth: AuthContext, query?: CatalogListQuery) {
  return requestJson<Paginated<Department>>(
    baseUrl,
    `${API_PREFIX}/departments` +
      queryString({
        status: query?.status,
        search: query?.search,
        cursor: query?.cursor,
        limit: query?.limit,
      }),
    {},
    auth,
  );
}

export function createDepartment(baseUrl: string, auth: AuthContext, body: { code: string; name: string }) {
  return requestJson<Department>(
    baseUrl,
    `${API_PREFIX}/departments`,
    { method: "POST", body: JSON.stringify(body) },
    auth,
  );
}

export function getDepartment(baseUrl: string, auth: AuthContext, departmentId: string) {
  return requestJson<Department>(baseUrl, `${API_PREFIX}/departments/${departmentId}`, {}, auth);
}

export function patchDepartment(
  baseUrl: string,
  auth: AuthContext,
  departmentId: string,
  body: { name?: string | null; status?: "active" | "inactive" | null },
) {
  return requestJson<Department>(
    baseUrl,
    `${API_PREFIX}/departments/${departmentId}`,
    { method: "PATCH", body: JSON.stringify(body) },
    auth,
  );
}

export function listCostCenters(baseUrl: string, auth: AuthContext, query?: CatalogListQuery) {
  return requestJson<Paginated<CostCenter>>(
    baseUrl,
    `${API_PREFIX}/cost-centers` +
      queryString({
        status: query?.status,
        search: query?.search,
        cursor: query?.cursor,
        limit: query?.limit,
      }),
    {},
    auth,
  );
}

export function createCostCenter(baseUrl: string, auth: AuthContext, body: { code: string; name: string }) {
  return requestJson<CostCenter>(
    baseUrl,
    `${API_PREFIX}/cost-centers`,
    { method: "POST", body: JSON.stringify(body) },
    auth,
  );
}

export function getCostCenter(baseUrl: string, auth: AuthContext, costCenterId: string) {
  return requestJson<CostCenter>(baseUrl, `${API_PREFIX}/cost-centers/${costCenterId}`, {}, auth);
}

export function patchCostCenter(
  baseUrl: string,
  auth: AuthContext,
  costCenterId: string,
  body: { name?: string | null; status?: "active" | "inactive" | null },
) {
  return requestJson<CostCenter>(
    baseUrl,
    `${API_PREFIX}/cost-centers/${costCenterId}`,
    { method: "PATCH", body: JSON.stringify(body) },
    auth,
  );
}

export function listBudgetVersions(
  baseUrl: string,
  auth: AuthContext,
  query?: { fiscal_year?: number; include_archived?: boolean; cursor?: string; limit?: number },
) {
  return requestJson<Paginated<BudgetVersion>>(
    baseUrl,
    `${API_PREFIX}/budget-versions` +
      queryString({
        fiscal_year: query?.fiscal_year,
        include_archived: query?.include_archived,
        cursor: query?.cursor,
        limit: query?.limit,
      }),
    {},
    auth,
  );
}

export function createBudgetVersion(baseUrl: string, auth: AuthContext, body: { name: string; fiscal_year: number }) {
  return requestJson<BudgetVersion>(
    baseUrl,
    `${API_PREFIX}/budget-versions`,
    { method: "POST", body: JSON.stringify(body) },
    auth,
  );
}

export function getBudgetVersion(baseUrl: string, auth: AuthContext, versionId: string) {
  return requestJson<BudgetVersion>(baseUrl, `${API_PREFIX}/budget-versions/${versionId}`, {}, auth);
}

export function patchBudgetVersion(
  baseUrl: string,
  auth: AuthContext,
  versionId: string,
  body: { version: number; name: string },
) {
  return requestJson<BudgetVersion>(
    baseUrl,
    `${API_PREFIX}/budget-versions/${versionId}`,
    { method: "PATCH", body: JSON.stringify(body) },
    auth,
  );
}

export function publishBudgetVersion(baseUrl: string, auth: AuthContext, versionId: string) {
  return requestJson<BudgetVersion>(
    baseUrl,
    `${API_PREFIX}/budget-versions/${versionId}/publish`,
    { method: "POST" },
    { ...auth, idempotencyKey: auth.idempotencyKey ?? crypto.randomUUID() },
  );
}

export function activateBudgetVersion(baseUrl: string, auth: AuthContext, versionId: string) {
  return requestJson<BudgetVersion>(
    baseUrl,
    `${API_PREFIX}/budget-versions/${versionId}/activate`,
    { method: "POST" },
    { ...auth, idempotencyKey: auth.idempotencyKey ?? crypto.randomUUID() },
  );
}

export function archiveBudgetVersion(baseUrl: string, auth: AuthContext, versionId: string) {
  return requestJson<BudgetVersion>(
    baseUrl,
    `${API_PREFIX}/budget-versions/${versionId}/archive`,
    { method: "POST" },
    { ...auth, idempotencyKey: auth.idempotencyKey ?? crypto.randomUUID() },
  );
}

export type ImportJob = {
  id: string;
  organization_id: string;
  import_type: string;
  budget_version_id: string | null;
  status: string;
  original_filename: string;
  sha256: string;
  sha256_short: string;
  size_bytes: number;
  template_version: string;
  mapping: Record<string, unknown>;
  row_count: number;
  valid_count: number;
  error_count: number;
  warning_count: number;
  period_min: string | null;
  period_max: string | null;
  valid_amount_total: string;
  sheet_name: string | null;
  failure_code: string | null;
  created_at: string;
  upload?: { mode: string; method: string; url: string } | null;
};

export type ImportErrorGroup = {
  code: string;
  severity: string;
  count: number;
  sample_message: string;
};

export type ImportPreview = {
  job: ImportJob;
  headers: string[];
  proposed_mapping: Record<string, string>;
  items: Array<Record<string, string>>;
  new_accounts: number;
  new_departments: number;
  new_cost_centers: number;
  replaced_records: number;
  sha256_short: string;
  delimiter: string | null;
  delimiter_ambiguous: boolean;
  available_sheets: string[];
  error_groups: ImportErrorGroup[];
  page: PageInfo;
};

export type ImportErrorItem = {
  row_number: number;
  field: string;
  code: string;
  message: string;
  raw_value_redacted: string;
  severity: string;
};

export type VarianceMetrics = {
  budget_amount: string;
  actual_amount: string;
  variance_amount: string;
  variance_percent: string | null;
  variance_state: string;
  favorability: string;
};

export type VarianceSummary = {
  scope: {
    fiscal_year: number;
    period_from: string;
    period_to: string;
    budget_version_id: string;
    currency: string;
  };
  metrics: VarianceMetrics;
};

export type BreakdownItem = {
  group_id: string;
  group_code: string;
  group_name: string;
  metrics: VarianceMetrics;
};

export type ExportJob = {
  id: string;
  export_type: string;
  format: string;
  filename: string;
  status: string;
  created_at: string;
  expires_at: string;
  download_url: string;
};

export type Scenario = {
  id: string;
  name: string;
  baseline_type: string;
  budget_version_id: string | null;
  fiscal_year: number;
  status: string;
  created_at: string;
  updated_at: string;
  rules: Array<Record<string, unknown>>;
};

export type ScenarioPreview = {
  baseline: string;
  result: string;
  metrics: VarianceMetrics;
  monthly: Array<{ period: string; baseline: string; result: string }>;
};

export type Conversation = {
  id: string;
  title: string;
  context_filters: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type CopilotMessage = {
  message_id: string;
  answer: string;
  scope: Record<string, unknown>;
  evidence: Array<Record<string, unknown>>;
  limitations: string[];
  trace_id: string;
};

export type RepeatableId = string | string[];

export type AnalyticsQuery = {
  fiscal_year: number;
  period_from: string;
  period_to: string;
  budget_version_id: string;
  account_id?: RepeatableId;
  department_id?: RepeatableId;
  cost_center_id?: RepeatableId;
};

export type CatalogListQuery = {
  status?: string;
  search?: string;
  cursor?: string;
  limit?: number;
};

export type PageQuery = {
  cursor?: string;
  limit?: number;
};

function queryString(values: Record<string, string | number | boolean | undefined | null>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value === undefined || value === null || value === "") continue;
    params.set(key, String(value));
  }
  const text = params.toString();
  return text ? `?${text}` : "";
}

function appendIds(params: URLSearchParams, name: string, value?: RepeatableId): void {
  if (!value) return;
  const items = Array.isArray(value) ? value : [value];
  for (const item of items) {
    if (item) params.append(name, item);
  }
}

function analyticsQuery(query: AnalyticsQuery): string {
  const params = new URLSearchParams({
    fiscal_year: String(query.fiscal_year),
    period_from: query.period_from,
    period_to: query.period_to,
    budget_version_id: query.budget_version_id,
  });
  appendIds(params, "account_id", query.account_id);
  appendIds(params, "department_id", query.department_id);
  appendIds(params, "cost_center_id", query.cost_center_id);
  return params.toString();
}

export function createImportJob(
  baseUrl: string,
  auth: AuthContext,
  body: {
    import_type: "budget" | "actual";
    budget_version_id?: string | null;
    original_filename: string;
    size_bytes: number;
    sha256: string;
    template_version?: string;
  },
) {
  return requestJson<ImportJob>(baseUrl, `${API_PREFIX}/imports`, { method: "POST", body: JSON.stringify(body) }, auth);
}

export async function uploadImportContent(baseUrl: string, auth: AuthContext, jobId: string, file: Blob, mediaType: string) {
  const headers = new Headers();
  headers.set("Authorization", `Bearer ${auth.token}`);
  if (auth.organizationId) headers.set("X-Organization-Id", auth.organizationId);
  headers.set("Content-Type", mediaType);
  const response = await fetch(apiUrl(baseUrl, `${API_PREFIX}/imports/${jobId}/content`), {
    method: "PUT",
    headers,
    body: file,
  });
  const data = (await response.json()) as ImportJob | ApiErrorEnvelope;
  if (response.status >= 400) {
    const envelope = data as ApiErrorEnvelope;
    throw new ApiRequestError(
      envelope.error?.message ?? "La solicitud no se pudo completar.",
      response.status,
      envelope.trace_id ?? readTraceId(response),
      envelope.error?.code ?? null,
    );
  }
  return { data: data as ImportJob, traceId: readTraceId(response), status: response.status };
}

export function validateImport(
  baseUrl: string,
  auth: AuthContext,
  jobId: string,
  body: {
    mapping: Record<string, string>;
    create_missing_dimensions?: boolean;
    amount_locale?: "en" | "es";
    sheet_name?: string | null;
    delimiter?: "," | ";" | "\t" | null;
  },
) {
  return requestJson<ImportJob>(
    baseUrl,
    `${API_PREFIX}/imports/${jobId}/validate`,
    { method: "POST", body: JSON.stringify(body) },
    auth,
  );
}

export function getImport(baseUrl: string, auth: AuthContext, jobId: string) {
  return requestJson<ImportJob>(baseUrl, `${API_PREFIX}/imports/${jobId}`, {}, auth);
}

export function previewImport(baseUrl: string, auth: AuthContext, jobId: string, query?: PageQuery) {
  return requestJson<ImportPreview>(
    baseUrl,
    `${API_PREFIX}/imports/${jobId}/preview` + queryString({ cursor: query?.cursor, limit: query?.limit }),
    {},
    auth,
  );
}

export function listImportErrors(baseUrl: string, auth: AuthContext, jobId: string) {
  return requestJson<Paginated<ImportErrorItem>>(baseUrl, `${API_PREFIX}/imports/${jobId}/errors`, {}, auth);
}

export function commitImport(baseUrl: string, auth: AuthContext, jobId: string) {
  return requestJson<ImportJob>(
    baseUrl,
    `${API_PREFIX}/imports/${jobId}/commit`,
    { method: "POST" },
    { ...auth, idempotencyKey: auth.idempotencyKey ?? crypto.randomUUID() },
  );
}

export function cancelImport(baseUrl: string, auth: AuthContext, jobId: string) {
  return requestJson<ImportJob>(baseUrl, `${API_PREFIX}/imports/${jobId}/cancel`, { method: "POST" }, auth);
}

export function importErrorReportUrl(baseUrl: string, jobId: string) {
  return apiUrl(baseUrl, `${API_PREFIX}/imports/${jobId}/error-report`);
}

export function getVarianceSummary(baseUrl: string, auth: AuthContext, query: AnalyticsQuery) {
  return requestJson<VarianceSummary>(baseUrl, `${API_PREFIX}/analytics/variance-summary?${analyticsQuery(query)}`, {}, auth);
}

export function getVarianceBreakdown(
  baseUrl: string,
  auth: AuthContext,
  query: AnalyticsQuery,
  groupBy: string,
  options?: { sort?: string; direction?: string; cursor?: string; limit?: number },
) {
  const extra = queryString({
    sort: options?.sort,
    direction: options?.direction,
    cursor: options?.cursor,
    limit: options?.limit,
  });
  const suffix = extra ? extra.replace("?", "&") : "";
  return requestJson<Paginated<BreakdownItem>>(
    baseUrl,
    `${API_PREFIX}/analytics/variance-breakdown?${analyticsQuery(query)}&group_by=${groupBy}${suffix}`,
    {},
    auth,
  );
}

export function getTopUnfavorable(
  baseUrl: string,
  auth: AuthContext,
  query: AnalyticsQuery,
  groupBy = "account",
  limit?: number,
) {
  const extra = queryString({ limit });
  const suffix = extra ? extra.replace("?", "&") : "";
  return requestJson<Paginated<BreakdownItem>>(
    baseUrl,
    `${API_PREFIX}/analytics/top-unfavorable?${analyticsQuery(query)}&group_by=${groupBy}${suffix}`,
    {},
    auth,
  );
}

export function createExport(baseUrl: string, auth: AuthContext, filters: AnalyticsQuery, groupBy: string) {
  return requestJson<ExportJob>(
    baseUrl,
    `${API_PREFIX}/exports`,
    {
      method: "POST",
      body: JSON.stringify({
        export_type: "variance_breakdown",
        format: "csv",
        group_by: groupBy,
        filters: {
          fiscal_year: filters.fiscal_year,
          period_from: filters.period_from,
          period_to: filters.period_to,
          budget_version_id: filters.budget_version_id,
          account_ids: filters.account_id ? [filters.account_id] : [],
          department_ids: filters.department_id ? [filters.department_id] : [],
          cost_center_ids: filters.cost_center_id ? [filters.cost_center_id] : [],
        },
      }),
    },
    auth,
  );
}

export function exportDownloadUrl(baseUrl: string, exportId: string) {
  return apiUrl(baseUrl, `${API_PREFIX}/exports/${exportId}/content`);
}

export function listScenarios(baseUrl: string, auth: AuthContext, query?: PageQuery) {
  return requestJson<Paginated<Scenario>>(
    baseUrl,
    `${API_PREFIX}/scenarios` + queryString({ cursor: query?.cursor, limit: query?.limit }),
    {},
    auth,
  );
}

export function getScenario(baseUrl: string, auth: AuthContext, scenarioId: string) {
  return requestJson<Scenario>(baseUrl, `${API_PREFIX}/scenarios/${scenarioId}`, {}, auth);
}

export function patchScenario(
  baseUrl: string,
  auth: AuthContext,
  scenarioId: string,
  body: { name?: string | null; rules?: Array<Record<string, unknown>> | null },
) {
  return requestJson<Scenario>(
    baseUrl,
    `${API_PREFIX}/scenarios/${scenarioId}`,
    { method: "PATCH", body: JSON.stringify(body) },
    auth,
  );
}

export function archiveScenario(baseUrl: string, auth: AuthContext, scenarioId: string) {
  return requestJson<Scenario>(baseUrl, `${API_PREFIX}/scenarios/${scenarioId}/archive`, { method: "POST" }, auth);
}

export function previewScenario(
  baseUrl: string,
  auth: AuthContext,
  body: {
    fiscal_year: number;
    period_from: string;
    period_to: string;
    budget_version_id: string;
    baseline_type: "budget" | "actual";
    department_ids?: string[];
    rules: Array<{
      sequence: number;
      operation: "percentage_change" | "absolute_change";
      value: string;
      scope: Record<string, unknown>;
    }>;
  },
) {
  return requestJson<ScenarioPreview>(baseUrl, `${API_PREFIX}/scenarios/preview`, { method: "POST", body: JSON.stringify(body) }, auth);
}

export function createScenario(
  baseUrl: string,
  auth: AuthContext,
  body: {
    name: string;
    baseline_type: "budget" | "actual";
    budget_version_id: string;
    fiscal_year: number;
    rules: Array<Record<string, unknown>>;
  },
) {
  return requestJson<Scenario>(baseUrl, `${API_PREFIX}/scenarios`, { method: "POST", body: JSON.stringify(body) }, auth);
}

export function listConversations(baseUrl: string, auth: AuthContext, query?: PageQuery) {
  return requestJson<Paginated<Conversation>>(
    baseUrl,
    `${API_PREFIX}/conversations` + queryString({ cursor: query?.cursor, limit: query?.limit }),
    {},
    auth,
  );
}

export function getConversation(baseUrl: string, auth: AuthContext, conversationId: string) {
  return requestJson<Conversation>(baseUrl, `${API_PREFIX}/conversations/${conversationId}`, {}, auth);
}

export function deleteConversation(baseUrl: string, auth: AuthContext, conversationId: string) {
  return requestJson<Conversation>(
    baseUrl,
    `${API_PREFIX}/conversations/${conversationId}`,
    { method: "DELETE" },
    auth,
  );
}

export type AuditEvent = {
  id: string;
  actor_id: string;
  action: string;
  resource_type: string;
  resource_id: string;
  outcome: string;
  metadata: Record<string, unknown>;
  trace_id: string;
  created_at: string;
};

export function listAuditEvents(
  baseUrl: string,
  auth: AuthContext,
  query?: {
    action?: string;
    actor_id?: string;
    resource_type?: string;
    date_from?: string;
    date_to?: string;
    cursor?: string;
    limit?: number;
  },
) {
  return requestJson<Paginated<AuditEvent>>(
    baseUrl,
    `${API_PREFIX}/audit-events` +
      queryString({
        action: query?.action,
        actor_id: query?.actor_id,
        resource_type: query?.resource_type,
        date_from: query?.date_from,
        date_to: query?.date_to,
        cursor: query?.cursor,
        limit: query?.limit,
      }),
    {},
    auth,
  );
}

export function createConversation(baseUrl: string, auth: AuthContext, body: { title?: string; context: Record<string, unknown> }) {
  return requestJson<Conversation>(baseUrl, `${API_PREFIX}/conversations`, { method: "POST", body: JSON.stringify(body) }, auth);
}

export function sendConversationMessage(
  baseUrl: string,
  auth: AuthContext,
  conversationId: string,
  body: { content: string; context: Record<string, unknown> },
) {
  return requestJson<CopilotMessage>(
    baseUrl,
    `${API_PREFIX}/conversations/${conversationId}/messages`,
    { method: "POST", body: JSON.stringify(body) },
    auth,
  );
}

export async function sha256Hex(file: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", file);
  return Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
}

export async function downloadAuthorized(url: string, auth: AuthContext, filename: string): Promise<void> {
  const headers = new Headers();
  headers.set("Authorization", `Bearer ${auth.token}`);
  if (auth.organizationId) {
    headers.set("X-Organization-Id", auth.organizationId);
  }
  const response = await fetch(url, { headers });
  if (!response.ok) {
    throw new ApiRequestError("No se pudo descargar el archivo.", response.status, readTraceId(response));
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(objectUrl);
}
