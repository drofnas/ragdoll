import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiProblemError,
  buildQueryString,
  configureApiClientAuth,
  createApiClient
} from "../client";

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
    configureApiClientAuth({});
  });

  it("builds query strings for scope and pagination params", () => {
    expect(
      buildQueryString({
        all_spaces: true,
        file_type: "pdf",
        page: 2,
        space_id: null
      })
    ).toBe("?all_spaces=true&file_type=pdf&page=2");
  });

  it("injects bearer auth headers on authenticated requests", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        headers: { "Content-Type": "application/json" },
        status: 200
      })
    );
    vi.stubGlobal("fetch", fetchMock);
    configureApiClientAuth({
      getAccessToken: () => "secret-token"
    });

    const client = createApiClient("http://example.test");
    await client.getJson("/api/v1/test");

    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    const headers = requestInit.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer secret-token");
  });

  it("submits login payloads as form-urlencoded content", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ access_token: "abc", token_type: "bearer" }), {
        headers: { "Content-Type": "application/json" },
        status: 200
      })
    );
    vi.stubGlobal("fetch", fetchMock);

    const client = createApiClient("http://example.test");
    await client.postForm("/api/v1/auth/login", {
      password: "secret",
      username: "user@example.com"
    });

    const requestInit = fetchMock.mock.calls[0]?.[1] as RequestInit;
    expect((requestInit.headers as Headers).get("Content-Type")).toBe(
      "application/x-www-form-urlencoded"
    );
    expect(String(requestInit.body)).toContain("username=user%40example.com");
  });

  it("returns blobs for download routes", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        blob: async () => new Blob(["hello"]),
        ok: true,
        status: 200
      })
    );

    const client = createApiClient("http://example.test");
    const blob = await client.getBlob("/api/v1/documents/doc-1/download");

    expect(await blob.text()).toBe("hello");
  });

  it("normalizes structured problem responses and triggers unauthorized handling", async () => {
    const unauthorizedSpy = vi.fn();
    configureApiClientAuth({
      getAccessToken: () => "secret-token",
      onUnauthorized: unauthorizedSpy
    });
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            detail: "Authentication required",
            instance: "/api/v1/account",
            status: 401,
            title: "Authentication required",
            type: "https://ragdoll.dev/problems/authentication-required"
          }),
          {
            headers: { "Content-Type": "application/json" },
            status: 401
          }
        )
      )
    );

    const client = createApiClient("http://example.test");
    await expect(client.getJson("/api/v1/account")).rejects.toBeInstanceOf(ApiProblemError);
    expect(unauthorizedSpy).toHaveBeenCalledTimes(1);
  });
});
