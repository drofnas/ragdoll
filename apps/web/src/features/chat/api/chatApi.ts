import type {
  ChatSendMessageResponse,
  ChatSessionDetail,
  ChatSessionListResponse,
  ChatSessionSummary,
  CorrectionCreateRequest,
  CorrectionRecordResponse,
  PostChatMessageApiV1ChatSessionsSessionIdMessagesPostOperation,
  PostChatSessionApiV1ChatSessionsPostOperation,
  PostCorrectionApiV1CorrectionsPostOperation,
  ReadChatSessionDetailApiV1ChatSessionsSessionIdGetOperation,
  ReadChatSessionsApiV1ChatSessionsGetOperation
} from "@contracts";

import { apiClient } from "../../../shared/api/client";

export type ListChatSessionsQuery = ReadChatSessionsApiV1ChatSessionsGetOperation["queryParams"];
export type CreateChatSessionQuery = PostChatSessionApiV1ChatSessionsPostOperation["queryParams"];
export type ChatSessionPathParams = ReadChatSessionDetailApiV1ChatSessionsSessionIdGetOperation["pathParams"];
export type SendChatMessagePayload = PostChatMessageApiV1ChatSessionsSessionIdMessagesPostOperation["requestBody"];
export type CreateCorrectionPayload = PostCorrectionApiV1CorrectionsPostOperation["requestBody"];
export type CreateCorrectionQuery = PostCorrectionApiV1CorrectionsPostOperation["queryParams"];

export function listChatSessions(query: ListChatSessionsQuery) {
  return apiClient.getJson<ChatSessionListResponse>("/api/v1/chat/sessions", { query });
}

export function createChatSession(query: CreateChatSessionQuery) {
  return apiClient.postJson<ChatSessionSummary, Record<string, never>>(
    "/api/v1/chat/sessions",
    {},
    { query }
  );
}

export function readChatSession(sessionId: ChatSessionPathParams["session_id"]) {
  return apiClient.getJson<ChatSessionDetail>(`/api/v1/chat/sessions/${sessionId}`);
}

export function sendChatMessage(
  sessionId: ChatSessionPathParams["session_id"],
  payload: SendChatMessagePayload
) {
  return apiClient.postJson<ChatSendMessageResponse, SendChatMessagePayload>(
    `/api/v1/chat/sessions/${sessionId}/messages`,
    payload
  );
}

export function createCorrection(
  payload: CreateCorrectionPayload,
  query: CreateCorrectionQuery
) {
  return apiClient.postJson<CorrectionRecordResponse, CorrectionCreateRequest>(
    "/api/v1/corrections",
    payload,
    { query }
  );
}
