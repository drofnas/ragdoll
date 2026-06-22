import type { ProblemResponse } from "@contracts";

export const DEFAULT_API_BASE_URL = "http://localhost:8031";

type PrimitiveQueryValue = string | number | boolean | null | undefined | Date;
type QueryValue = PrimitiveQueryValue | PrimitiveQueryValue[];

export interface ApiRequestOptions {
  auth?: boolean;
  body?: BodyInit | null;
  headers?: HeadersInit;
  method?: string;
  query?: Record<string, QueryValue>;
  responseType?: "blob" | "json" | "text";
  signal?: AbortSignal;
}

interface ApiClientAuthConfig {
  getAccessToken?: () => string | null;
  onUnauthorized?: () => void;
}

const authConfig: Required<ApiClientAuthConfig> = {
  getAccessToken: () => null,
  onUnauthorized: () => undefined
};

export function configureApiClientAuth(config: ApiClientAuthConfig) {
  authConfig.getAccessToken = config.getAccessToken ?? (() => null);
  authConfig.onUnauthorized = config.onUnauthorized ?? (() => undefined);
}

export function resolveApiBaseUrl(baseUrl = import.meta.env.VITE_API_URL || DEFAULT_API_BASE_URL) {
  return baseUrl.replace(/\/$/, "");
}

function toQueryEntry(value: PrimitiveQueryValue): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  if (value instanceof Date) {
    return value.toISOString();
  }
  return String(value);
}

export function buildQueryString(query?: Record<string, QueryValue>) {
  const params = new URLSearchParams();

  if (!query) {
    return "";
  }

  for (const [key, rawValue] of Object.entries(query)) {
    if (Array.isArray(rawValue)) {
      for (const value of rawValue) {
        const resolved = toQueryEntry(value);
        if (resolved !== null) {
          params.append(key, resolved);
        }
      }
      continue;
    }

    const resolved = toQueryEntry(rawValue);
    if (resolved !== null) {
      params.append(key, resolved);
    }
  }

  const search = params.toString();
  return search ? `?${search}` : "";
}

export class ApiProblemError extends Error {
  readonly problem: ProblemResponse;
  readonly status: number;

  constructor(problem: ProblemResponse) {
    super(problem.detail);
    this.name = "ApiProblemError";
    this.problem = problem;
    this.status = problem.status;
  }
}

export function normalizeProblemResponse(
  payload: unknown,
  fallbackStatus: number,
  fallbackInstance: string
): ProblemResponse {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "type" in payload &&
    "title" in payload &&
    "status" in payload &&
    "detail" in payload &&
    "instance" in payload
  ) {
    return payload as ProblemResponse;
  }

  return {
    type: "https://ragdoll.dev/problems/http-error",
    title: "HTTP request failed",
    status: fallbackStatus,
    detail: "The request failed without a structured problem response.",
    instance: fallbackInstance,
    code: "http_error"
  };
}

export function createApiClient(baseUrl = import.meta.env.VITE_API_URL || DEFAULT_API_BASE_URL) {
  const resolvedBaseUrl = resolveApiBaseUrl(baseUrl);

  async function request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    const urlPath = path.startsWith("/") ? path : `/${path}`;
    const url = `${resolvedBaseUrl}${urlPath}${buildQueryString(options.query)}`;
    const headers = new Headers(options.headers);

    if (options.auth !== false) {
      const accessToken = authConfig.getAccessToken();
      if (accessToken) {
        headers.set("Authorization", `Bearer ${accessToken}`);
      }
    }

    const response = await fetch(url, {
      method: options.method ?? "GET",
      body: options.body,
      headers,
      signal: options.signal
    });

    if (!response.ok) {
      let payload: unknown = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }

      if (response.status === 401 && options.auth !== false) {
        authConfig.onUnauthorized();
      }

      throw new ApiProblemError(normalizeProblemResponse(payload, response.status, url));
    }

    if (options.responseType === "blob") {
      return (await response.blob()) as T;
    }

    if (options.responseType === "text") {
      return (await response.text()) as T;
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  }

  function getJson<T>(path: string, options: Omit<ApiRequestOptions, "method" | "responseType"> = {}) {
    return request<T>(path, {
      ...options,
      method: "GET",
      responseType: "json"
    });
  }

  function getBlob(path: string, options: Omit<ApiRequestOptions, "method" | "responseType"> = {}) {
    return request<Blob>(path, {
      ...options,
      method: "GET",
      responseType: "blob"
    });
  }

  function postJson<TResponse, TRequest>(
    path: string,
    payload: TRequest,
    options: Omit<ApiRequestOptions, "body" | "method" | "responseType"> = {}
  ) {
    return request<TResponse>(path, {
      ...options,
      method: "POST",
      responseType: "json",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
        ...options.headers
      }
    });
  }

  function patchJson<TResponse, TRequest>(
    path: string,
    payload: TRequest,
    options: Omit<ApiRequestOptions, "body" | "method" | "responseType"> = {}
  ) {
    return request<TResponse>(path, {
      ...options,
      method: "PATCH",
      responseType: "json",
      body: JSON.stringify(payload),
      headers: {
        "Content-Type": "application/json",
        ...options.headers
      }
    });
  }

  function deleteJson<TResponse>(path: string, options: Omit<ApiRequestOptions, "method" | "responseType"> = {}) {
    return request<TResponse>(path, {
      ...options,
      method: "DELETE",
      responseType: "json"
    });
  }

  function postForm<TResponse>(
    path: string,
    payload: Record<string, string>,
    options: Omit<ApiRequestOptions, "body" | "method" | "responseType"> = {}
  ) {
    return request<TResponse>(path, {
      ...options,
      method: "POST",
      responseType: "json",
      body: new URLSearchParams(payload),
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        ...options.headers
      }
    });
  }

  function postMultipart<TResponse>(
    path: string,
    payload: FormData,
    options: Omit<ApiRequestOptions, "body" | "method" | "responseType"> = {}
  ) {
    return request<TResponse>(path, {
      ...options,
      method: "POST",
      responseType: "json",
      body: payload
    });
  }

  return {
    baseUrl: resolvedBaseUrl,
    buildQueryString,
    deleteJson,
    getBlob,
    getJson,
    patchJson,
    postForm,
    postJson,
    postMultipart,
    request
  };
}

export const apiClient = createApiClient();
