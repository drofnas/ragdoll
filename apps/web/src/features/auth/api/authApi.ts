import type {
  LoginTokenResponse,
  PatchCurrentUserApiV1AuthMePatchOperation,
  RegisterRequest,
  UserProfileResponse
} from "@contracts";

import { apiClient } from "../../../shared/api/client";

export type UpdateCurrentUserPayload = PatchCurrentUserApiV1AuthMePatchOperation["requestBody"];

export function registerUser(payload: RegisterRequest) {
  return apiClient.postJson<UserProfileResponse, RegisterRequest>("/api/v1/auth/register", payload, {
    auth: false
  });
}

export function updateCurrentUser(payload: UpdateCurrentUserPayload) {
  return apiClient.patchJson<UserProfileResponse, UpdateCurrentUserPayload>("/api/v1/auth/me", payload);
}

export function loginUser(payload: { password: string; username: string }) {
  return apiClient.postForm<LoginTokenResponse>("/api/v1/auth/login", payload, {
    auth: false
  });
}
