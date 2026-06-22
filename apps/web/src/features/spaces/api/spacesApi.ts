import type {
  PatchSpaceApiV1SpacesSpaceIdPatchOperation,
  PostSpaceApiV1SpacesPostOperation,
  SpaceListResponse,
  SpaceResponse
} from "@contracts";

import { apiClient } from "../../../shared/api/client";

export type CreateSpacePayload = PostSpaceApiV1SpacesPostOperation["requestBody"];
export type UpdateSpacePayload = PatchSpaceApiV1SpacesSpaceIdPatchOperation["requestBody"];

export function listSpaces(includeArchived = true) {
  return apiClient.getJson<SpaceListResponse>("/api/v1/spaces", {
    query: {
      include_archived: includeArchived
    }
  });
}

export function createSpace(payload: CreateSpacePayload) {
  return apiClient.postJson<SpaceResponse, CreateSpacePayload>("/api/v1/spaces", payload);
}

export function updateSpace(spaceId: string, payload: UpdateSpacePayload) {
  return apiClient.patchJson<SpaceResponse, UpdateSpacePayload>(`/api/v1/spaces/${spaceId}`, payload);
}

export function archiveSpace(spaceId: string) {
  return apiClient.deleteJson<SpaceResponse>(`/api/v1/spaces/${spaceId}`);
}
