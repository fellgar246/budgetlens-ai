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

export function getDevIdentities(baseUrl: string) {
  return requestJson<{ users: DevIdentity[] }>(baseUrl, `${API_PREFIX}/dev/identities`);
}

export function getMe(baseUrl: string, auth: AuthContext) {
  return requestJson<MeResponse>(baseUrl, `${API_PREFIX}/me`, {}, auth);
}

export function listOrganizations(baseUrl: string, auth: AuthContext) {
  return requestJson<Paginated<Organization>>(baseUrl, `${API_PREFIX}/organizations`, {}, auth);
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
  },
) {
  return requestJson<Organization>(
    baseUrl,
    `${API_PREFIX}/organizations/${organizationId}`,
    { method: "PATCH", body: JSON.stringify(body) },
    auth,
  );
}

export function listMemberships(baseUrl: string, auth: AuthContext) {
  return requestJson<Paginated<Membership>>(baseUrl, `${API_PREFIX}/memberships`, {}, auth);
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

export function listAccounts(baseUrl: string, auth: AuthContext) {
  return requestJson<Paginated<Account>>(baseUrl, `${API_PREFIX}/accounts`, {}, auth);
}

export function createAccount(
  baseUrl: string,
  auth: AuthContext,
  body: { code: string; name: string; account_type: string },
) {
  return requestJson<Account>(baseUrl, `${API_PREFIX}/accounts`, { method: "POST", body: JSON.stringify(body) }, auth);
}

export function listDepartments(baseUrl: string, auth: AuthContext) {
  return requestJson<Paginated<Department>>(baseUrl, `${API_PREFIX}/departments`, {}, auth);
}

export function createDepartment(baseUrl: string, auth: AuthContext, body: { code: string; name: string }) {
  return requestJson<Department>(
    baseUrl,
    `${API_PREFIX}/departments`,
    { method: "POST", body: JSON.stringify(body) },
    auth,
  );
}

export function listCostCenters(baseUrl: string, auth: AuthContext) {
  return requestJson<Paginated<CostCenter>>(baseUrl, `${API_PREFIX}/cost-centers`, {}, auth);
}

export function createCostCenter(baseUrl: string, auth: AuthContext, body: { code: string; name: string }) {
  return requestJson<CostCenter>(
    baseUrl,
    `${API_PREFIX}/cost-centers`,
    { method: "POST", body: JSON.stringify(body) },
    auth,
  );
}

export function listBudgetVersions(baseUrl: string, auth: AuthContext) {
  return requestJson<Paginated<BudgetVersion>>(baseUrl, `${API_PREFIX}/budget-versions`, {}, auth);
}

export function createBudgetVersion(baseUrl: string, auth: AuthContext, body: { name: string; fiscal_year: number }) {
  return requestJson<BudgetVersion>(
    baseUrl,
    `${API_PREFIX}/budget-versions`,
    { method: "POST", body: JSON.stringify(body) },
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

export type ImportPreview = {
  job: ImportJob;
  headers: string[];
  proposed_mapping: Record<string, string>;
  items: Array<Record<string, string>>;
  new_accounts: number;
  new_departments: number;
  new_cost_centers: number;
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

export type AnalyticsQuery = {
  fiscal_year: number;
  period_from: string;
  period_to: string;
  budget_version_id: string;
  account_id?: string;
  department_id?: string;
  cost_center_id?: string;
};

function analyticsQuery(query: AnalyticsQuery): string {
  const params = new URLSearchParams({
    fiscal_year: String(query.fiscal_year),
    period_from: query.period_from,
    period_to: query.period_to,
    budget_version_id: query.budget_version_id,
  });
  if (query.account_id) params.append("account_id", query.account_id);
  if (query.department_id) params.append("department_id", query.department_id);
  if (query.cost_center_id) params.append("cost_center_id", query.cost_center_id);
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
  body: { mapping: Record<string, string>; create_missing_dimensions?: boolean; amount_locale?: "en" | "es" },
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

export function previewImport(baseUrl: string, auth: AuthContext, jobId: string) {
  return requestJson<ImportPreview>(baseUrl, `${API_PREFIX}/imports/${jobId}/preview`, {}, auth);
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
) {
  return requestJson<Paginated<BreakdownItem>>(
    baseUrl,
    `${API_PREFIX}/analytics/variance-breakdown?${analyticsQuery(query)}&group_by=${groupBy}`,
    {},
    auth,
  );
}

export function getTopUnfavorable(baseUrl: string, auth: AuthContext, query: AnalyticsQuery, groupBy = "account") {
  return requestJson<Paginated<BreakdownItem>>(
    baseUrl,
    `${API_PREFIX}/analytics/top-unfavorable?${analyticsQuery(query)}&group_by=${groupBy}`,
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
