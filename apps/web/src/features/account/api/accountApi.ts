import type { UsageSummaryResponse } from "@contracts";

import { apiClient } from "../../../shared/api/client";

export function readUsageSummary() {
  return apiClient.getJson<UsageSummaryResponse>("/api/v1/usage/me");
}
