import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiProblemError, createApiClient } from "../client";

describe("api client", () => {
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("normalizes structured problem responses", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        json: async () => ({
          type: "https://ragdoll.dev/problems/request-validation",
          title: "Request validation failed",
          status: 422,
          detail: "Payload invalid",
          instance: "http://example.test/api"
        })
      })
    );

    const client = createApiClient("http://example.test");

    await expect(client.request("/api/v1/test")).rejects.toBeInstanceOf(ApiProblemError);
  });
});
