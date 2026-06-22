import type {
  PatchTrackedFieldApiV1TrackedStateFieldsFieldIdPatchOperation,
  PostTrackedFieldApiV1TrackedStateFieldsPostOperation,
  PostRecomputeTrackedFieldApiV1TrackedStateFieldsFieldIdRecomputePostOperation,
  ReadTrackedConflictsApiV1TrackedStateConflictsGetOperation,
  ReadTrackedFieldsApiV1TrackedStateFieldsGetOperation,
  ReadTrackedSummaryApiV1TrackedStateSummaryGetOperation,
  TrackedFieldDefinition,
  TrackedFieldDefinitionListResponse,
  TrackedFieldSummary,
  TrackedStateConflictResponse,
  TrackedStateSummaryResponse
} from "@contracts";

import { apiClient } from "../../../shared/api/client";

export type ListTrackedFieldsQuery = ReadTrackedFieldsApiV1TrackedStateFieldsGetOperation["queryParams"];
export type CreateTrackedFieldQuery = PostTrackedFieldApiV1TrackedStateFieldsPostOperation["queryParams"];
export type CreateTrackedFieldPayload = PostTrackedFieldApiV1TrackedStateFieldsPostOperation["requestBody"];
export type UpdateTrackedFieldPathParams = PatchTrackedFieldApiV1TrackedStateFieldsFieldIdPatchOperation["pathParams"];
export type UpdateTrackedFieldQuery = PatchTrackedFieldApiV1TrackedStateFieldsFieldIdPatchOperation["queryParams"];
export type UpdateTrackedFieldPayload = PatchTrackedFieldApiV1TrackedStateFieldsFieldIdPatchOperation["requestBody"];
export type RecomputeTrackedFieldQuery = PostRecomputeTrackedFieldApiV1TrackedStateFieldsFieldIdRecomputePostOperation["queryParams"];
export type RecomputeTrackedFieldPathParams = PostRecomputeTrackedFieldApiV1TrackedStateFieldsFieldIdRecomputePostOperation["pathParams"];
export type TrackedSummaryQuery = ReadTrackedSummaryApiV1TrackedStateSummaryGetOperation["queryParams"];
export type TrackedConflictsQuery = ReadTrackedConflictsApiV1TrackedStateConflictsGetOperation["queryParams"];

export function listTrackedFields(query: ListTrackedFieldsQuery) {
  return apiClient.getJson<TrackedFieldDefinitionListResponse>("/api/v1/tracked-state/fields", {
    query
  });
}

export function createTrackedField(
  payload: CreateTrackedFieldPayload,
  query: CreateTrackedFieldQuery
) {
  return apiClient.postJson<TrackedFieldDefinition, CreateTrackedFieldPayload>(
    "/api/v1/tracked-state/fields",
    payload,
    { query }
  );
}

export function updateTrackedField(
  fieldId: UpdateTrackedFieldPathParams["field_id"],
  payload: UpdateTrackedFieldPayload,
  query: UpdateTrackedFieldQuery
) {
  return apiClient.patchJson<TrackedFieldDefinition, UpdateTrackedFieldPayload>(
    `/api/v1/tracked-state/fields/${fieldId}`,
    payload,
    { query }
  );
}

export function recomputeTrackedField(
  fieldId: RecomputeTrackedFieldPathParams["field_id"],
  query: RecomputeTrackedFieldQuery
) {
  return apiClient.postJson<TrackedFieldSummary, Record<string, never>>(
    `/api/v1/tracked-state/fields/${fieldId}/recompute`,
    {},
    { query }
  );
}

export function readTrackedSummary(query: TrackedSummaryQuery) {
  return apiClient.getJson<TrackedStateSummaryResponse>("/api/v1/tracked-state/summary", {
    query
  });
}

export function readTrackedConflicts(query: TrackedConflictsQuery) {
  return apiClient.getJson<TrackedStateConflictResponse>(
    "/api/v1/tracked-state/conflicts",
    { query }
  );
}
