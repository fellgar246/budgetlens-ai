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

export type MeResponse = {
  id: string;
  email: string;
  display_name: string;
  status: string;
  auth_mode: string;
  capabilities: {
    can_import: boolean;
    can_manage_versions: boolean;
    can_manage_dimensions: boolean;
    can_manage_members: boolean;
    can_manage_organization: boolean;
  };
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
  memberships: Array<{
    organization_id: string;
    organization_name: string;
    role: string;
  }>;
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
