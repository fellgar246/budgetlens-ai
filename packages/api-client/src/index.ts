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

export class ApiRequestError extends Error {
  readonly status: number;
  readonly traceId: string | null;

  constructor(message: string, status: number, traceId: string | null) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.traceId = traceId;
  }
}

export function apiUrl(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/$/, "")}${path}`;
}

function readTraceId(response: Response): string | null {
  return response.headers.get("X-Trace-Id") ?? response.headers.get("x-trace-id");
}

async function getJson<T>(baseUrl: string, path: string): Promise<{ data: T; traceId: string | null; status: number }> {
  let response: Response;
  try {
    response = await fetch(apiUrl(baseUrl, path), {
      method: "GET",
      headers: { Accept: "application/json" },
    });
  } catch {
    throw new ApiRequestError("No se pudo contactar la API.", 0, null);
  }

  const traceId = readTraceId(response);
  const data = (await response.json()) as T;
  return { data, traceId, status: response.status };
}

export function getLive(baseUrl: string) {
  return getJson<LiveStatusResponse>(baseUrl, `${API_PREFIX}/health/live`);
}

export function getReady(baseUrl: string) {
  return getJson<ReadyStatusResponse>(baseUrl, `${API_PREFIX}/health/ready`);
}

export function getVersion(baseUrl: string) {
  return getJson<VersionResponse>(baseUrl, `${API_PREFIX}/version`);
}
