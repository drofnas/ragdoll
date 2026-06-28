import type { RuntimeStatusResponse } from "@contracts";

import { apiClient } from "./client";

export function readRuntimeStatus() {
  return apiClient.getJson<RuntimeStatusResponse>("/status", {
    auth: false,
    query: { type: "json" },
  });
}
