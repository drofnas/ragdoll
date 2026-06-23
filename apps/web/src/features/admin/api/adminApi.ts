import type {
  AdminEffectiveLimitsResponse,
  AdminManagedUserListResponse,
  AdminManagedUserResponse,
  AdminUpdateUserRequest,
  RuntimeStatusResponse,
} from "@contracts";

import { apiClient } from "../../../shared/api/client";

export function readAdminUsers(page = 1, pageSize = 25) {
  return apiClient.getJson<AdminManagedUserListResponse>("/api/v1/admin/users", {
    query: { page, page_size: pageSize },
  });
}

export function readAdminUser(userId: string) {
  return apiClient.getJson<AdminManagedUserResponse>(`/api/v1/admin/users/${userId}`);
}

export function updateAdminUser(userId: string, payload: AdminUpdateUserRequest) {
  return apiClient.patchJson<AdminManagedUserResponse, AdminUpdateUserRequest>(
    `/api/v1/admin/users/${userId}`,
    payload
  );
}

export function readEffectiveLimits() {
  return apiClient.getJson<AdminEffectiveLimitsResponse>("/api/v1/admin/effective-limits");
}

export function readRuntimeStatus() {
  return apiClient.getJson<RuntimeStatusResponse>("/status", {
    auth: false,
    query: { type: "json" },
  });
}
