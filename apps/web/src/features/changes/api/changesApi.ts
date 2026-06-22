import type {
  ChangeEventDetail,
  ChangeEventReadResult,
  ChangeListResponse,
  CorrectionListResponse,
  CorrectionRecordResponse,
  CorrectionReviewRequest,
  PostCorrectionApiV1CorrectionsPostOperation,
  ReadChangeApiV1ChangesChangeIdReadPostOperation,
  ReadChangeDetailApiV1ChangesChangeIdGetOperation,
  ReadChangesApiV1ChangesGetOperation,
  ReadCorrectionDetailApiV1CorrectionsCorrectionIdGetOperation,
  ReadCorrectionsApiV1CorrectionsGetOperation,
  RejectCorrectionApiV1CorrectionsCorrectionIdRejectPostOperation,
  VerifyCorrectionApiV1CorrectionsCorrectionIdVerifyPostOperation
} from "@contracts";

import { apiClient } from "../../../shared/api/client";

export type ListChangesQuery = ReadChangesApiV1ChangesGetOperation["queryParams"];
export type ChangePathParams = ReadChangeDetailApiV1ChangesChangeIdGetOperation["pathParams"];
export type ChangeReadPathParams = ReadChangeApiV1ChangesChangeIdReadPostOperation["pathParams"];
export type ListCorrectionsQuery = ReadCorrectionsApiV1CorrectionsGetOperation["queryParams"];
export type CorrectionPathParams = ReadCorrectionDetailApiV1CorrectionsCorrectionIdGetOperation["pathParams"];
export type ReviewCorrectionPathParams = VerifyCorrectionApiV1CorrectionsCorrectionIdVerifyPostOperation["pathParams"];
export type ReviewCorrectionPayload = VerifyCorrectionApiV1CorrectionsCorrectionIdVerifyPostOperation["requestBody"];
export type RejectCorrectionPayload = RejectCorrectionApiV1CorrectionsCorrectionIdRejectPostOperation["requestBody"];
export type CreateCorrectionPayload = PostCorrectionApiV1CorrectionsPostOperation["requestBody"];

export function listChanges(query: ListChangesQuery) {
  return apiClient.getJson<ChangeListResponse>("/api/v1/changes", { query });
}

export function readChangeDetail(changeId: ChangePathParams["change_id"]) {
  return apiClient.getJson<ChangeEventDetail>(`/api/v1/changes/${changeId}`);
}

export function markChangeRead(changeId: ChangeReadPathParams["change_id"]) {
  return apiClient.postJson<ChangeEventReadResult, Record<string, never>>(
    `/api/v1/changes/${changeId}/read`,
    {}
  );
}

export function listCorrections(query: ListCorrectionsQuery) {
  return apiClient.getJson<CorrectionListResponse>("/api/v1/corrections", { query });
}

export function readCorrectionDetail(correctionId: CorrectionPathParams["correction_id"]) {
  return apiClient.getJson<CorrectionRecordResponse>(`/api/v1/corrections/${correctionId}`);
}

export function verifyCorrection(
  correctionId: ReviewCorrectionPathParams["correction_id"],
  payload: ReviewCorrectionPayload
) {
  return apiClient.postJson<CorrectionRecordResponse, CorrectionReviewRequest>(
    `/api/v1/corrections/${correctionId}/verify`,
    payload
  );
}

export function rejectCorrection(
  correctionId: ReviewCorrectionPathParams["correction_id"],
  payload: RejectCorrectionPayload
) {
  return apiClient.postJson<CorrectionRecordResponse, CorrectionReviewRequest>(
    `/api/v1/corrections/${correctionId}/reject`,
    payload
  );
}
