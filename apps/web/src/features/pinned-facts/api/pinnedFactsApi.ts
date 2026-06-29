import type {
  Citation,
  PinnedFactCandidate,
  PinnedFactCandidateListResponse,
  PinnedFactDetectionPreviewResponse,
  PinnedFactDetail,
  PinnedFactHistoryResponse,
  PinnedFactListResponse
} from "@contracts";

import { apiClient } from "../../../shared/api/client";

export interface FactScopeQuery {
  all_spaces?: boolean;
  created_by?: string;
  created_date?: string;
  descending?: boolean;
  name?: string;
  page?: number;
  page_size?: number;
  sort_key?: "created_at" | "created_by" | "name" | "status" | "updated_at" | "updated_by";
  space_id?: string;
  status?: string;
  updated_by?: string;
  updated_date?: string;
}

export interface PinnedFactEvidencePayload {
  citations: Citation[];
  quote: string;
  source_chunk_ids: string[];
}

export interface CreatePinnedFactPayload {
  confidence?: number | null;
  description: string;
  entity_type_hint?: string | null;
  evidence: PinnedFactEvidencePayload[];
  is_active?: boolean;
  key: string;
  source_document_id?: string | null;
  title: string;
  value_json?: Record<string, unknown> | null;
  value_kind: "json" | "text";
  value_text?: string | null;
}

export interface UpdatePinnedFactPayload {
  description?: string | null;
  evidence?: PinnedFactEvidencePayload[] | null;
  confidence?: number | null;
  entity_type_hint?: string | null;
  is_active?: boolean;
  source_document_id?: string | null;
  title?: string | null;
  update_note?: string | null;
  value_json?: Record<string, unknown> | null;
  value_kind?: "json" | "text" | null;
  value_text?: string | null;
}

export interface AcceptPinnedFactCandidatePayload {
  review_notes?: string | null;
  value_json?: Record<string, unknown> | null;
  value_kind?: "json" | "text" | null;
  value_text?: string | null;
}

export interface RejectPinnedFactCandidatePayload {
  review_notes?: string | null;
}

export interface PinnedFactDetectionPreviewPayload {
  description: string;
  entity_type_hint?: string | null;
}

export function listPinnedFacts(query: FactScopeQuery) {
  return apiClient.getJson<PinnedFactListResponse>("/api/v1/pinned-facts", { query });
}

export function createPinnedFact(payload: CreatePinnedFactPayload, query: FactScopeQuery) {
  return apiClient.postJson<PinnedFactDetail, CreatePinnedFactPayload>("/api/v1/pinned-facts", payload, {
    query
  });
}

export function previewPinnedFactDetection(payload: PinnedFactDetectionPreviewPayload, query: FactScopeQuery) {
  return apiClient.postJson<PinnedFactDetectionPreviewResponse, PinnedFactDetectionPreviewPayload>(
    "/api/v1/pinned-facts/detect-preview",
    payload,
    { query }
  );
}

export function readPinnedFact(factId: string, query: FactScopeQuery) {
  return apiClient.getJson<PinnedFactDetail>(`/api/v1/pinned-facts/${factId}`, { query });
}

export function updatePinnedFact(factId: string, payload: UpdatePinnedFactPayload, query: FactScopeQuery) {
  return apiClient.patchJson<PinnedFactDetail, UpdatePinnedFactPayload>(
    `/api/v1/pinned-facts/${factId}`,
    payload,
    { query }
  );
}

export function readPinnedFactCandidates(factId: string, query: FactScopeQuery) {
  return apiClient.getJson<PinnedFactCandidateListResponse>(`/api/v1/pinned-facts/${factId}/candidates`, {
    query
  });
}

export function readPinnedFactHistory(factId: string, query: FactScopeQuery) {
  return apiClient.getJson<PinnedFactHistoryResponse>(`/api/v1/pinned-facts/${factId}/history`, {
    query
  });
}

export function readPinnedFactCandidate(candidateId: string, query: FactScopeQuery) {
  return apiClient.getJson<PinnedFactCandidate>(`/api/v1/pinned-facts/candidates/${candidateId}`, { query });
}

export function acceptPinnedFactCandidate(
  candidateId: string,
  payload: AcceptPinnedFactCandidatePayload,
  query: FactScopeQuery
) {
  return apiClient.postJson<PinnedFactDetail, AcceptPinnedFactCandidatePayload>(
    `/api/v1/pinned-facts/candidates/${candidateId}/accept`,
    payload,
    { query }
  );
}

export function rejectPinnedFactCandidate(
  candidateId: string,
  payload: RejectPinnedFactCandidatePayload,
  query: FactScopeQuery
) {
  return apiClient.postJson<PinnedFactCandidate, RejectPinnedFactCandidatePayload>(
    `/api/v1/pinned-facts/candidates/${candidateId}/reject`,
    payload,
    { query }
  );
}

export function recheckPinnedFact(factId: string, query: FactScopeQuery) {
  return apiClient.postJson<PinnedFactDetail, Record<string, never>>(
    `/api/v1/pinned-facts/${factId}/recheck`,
    {},
    { query }
  );
}

export function revertPinnedFactHistory(factId: string, historyId: string, query: FactScopeQuery) {
  return apiClient.postJson<PinnedFactDetail, Record<string, never>>(
    `/api/v1/pinned-facts/${factId}/history/${historyId}/revert`,
    {},
    { query }
  );
}
