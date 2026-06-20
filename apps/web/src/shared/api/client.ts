import type { ProblemResponse } from "../types/app";

const DEFAULT_API_BASE_URL = "http://localhost:8031";

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

interface RequestOptions {
  method?: string;
  body?: BodyInit | null;
  headers?: HeadersInit;
  signal?: AbortSignal;
}

export function createApiClient(baseUrl = import.meta.env.VITE_API_URL || DEFAULT_API_BASE_URL) {
  const resolvedBaseUrl = baseUrl.replace(/\/$/, "");

  async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
    const url = `${resolvedBaseUrl}${path.startsWith("/") ? path : `/${path}`}`;
    const response = await fetch(url, {
      method: options.method ?? "GET",
      body: options.body,
      headers: options.headers,
      signal: options.signal
    });

    if (!response.ok) {
      let payload: unknown = null;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      throw new ApiProblemError(normalizeProblemResponse(payload, response.status, url));
    }

    return (await response.json()) as T;
  }

  return {
    baseUrl: resolvedBaseUrl,
    request
  };
}

export const apiClient = createApiClient();
