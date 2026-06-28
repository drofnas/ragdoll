import type {
  BatchDocumentStatusRequest,
  BatchDocumentStatusResponse,
  CreateUploadApiV1IngestionUploadsPostOperation,
  DocumentDetail,
  DocumentListResponse,
  DocumentProcessingStatusResponse,
  DownloadDocumentApiV1DocumentsDocumentIdDownloadGetOperation,
  MutationResult,
  PatchDocumentApiV1DocumentsDocumentIdPatchOperation,
  ReadBatchDocumentStatusApiV1IngestionDocumentsStatusBatchPostOperation,
  ReadDocumentApiV1DocumentsDocumentIdGetOperation,
  ReadDocumentStatusApiV1IngestionDocumentsDocumentIdStatusGetOperation,
  ReadDocumentsApiV1DocumentsGetOperation,
  UploadDocumentResponse
} from "@contracts";

import { apiClient } from "../../../shared/api/client";

export type ListDocumentsQuery = ReadDocumentsApiV1DocumentsGetOperation["queryParams"];
export type DocumentPathParams = ReadDocumentApiV1DocumentsDocumentIdGetOperation["pathParams"];
export type DocumentStatusPathParams = ReadDocumentStatusApiV1IngestionDocumentsDocumentIdStatusGetOperation["pathParams"];
export type BatchDocumentStatusPayload = ReadBatchDocumentStatusApiV1IngestionDocumentsStatusBatchPostOperation["requestBody"];
export type UploadDocumentQuery = CreateUploadApiV1IngestionUploadsPostOperation["queryParams"];
export type UpdateDocumentPayload = PatchDocumentApiV1DocumentsDocumentIdPatchOperation["requestBody"];
export type DownloadDocumentPathParams = DownloadDocumentApiV1DocumentsDocumentIdDownloadGetOperation["pathParams"];

export function listDocuments(query: ListDocumentsQuery) {
  return apiClient.getJson<DocumentListResponse>("/api/v1/documents", { query });
}

export function readDocument(documentId: DocumentPathParams["document_id"]) {
  return apiClient.getJson<DocumentDetail>(`/api/v1/documents/${documentId}`);
}

export function readDocumentStatus(documentId: DocumentStatusPathParams["document_id"]) {
  return apiClient.getJson<DocumentProcessingStatusResponse>(`/api/v1/ingestion/documents/${documentId}/status`);
}

export function readBatchDocumentStatuses(payload: BatchDocumentStatusRequest) {
  return apiClient.postJson<BatchDocumentStatusResponse, BatchDocumentStatusPayload>(
    "/api/v1/ingestion/documents/status/batch",
    payload
  );
}

export function reprocessDocument(documentId: DocumentStatusPathParams["document_id"]) {
  return apiClient.postJson<DocumentProcessingStatusResponse, Record<string, never>>(
    `/api/v1/ingestion/documents/${documentId}/reprocess`,
    {}
  );
}

export function uploadDocument(file: File, query: UploadDocumentQuery) {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient.postMultipart<UploadDocumentResponse>("/api/v1/ingestion/uploads", formData, { query });
}

export function moveDocument(documentId: string, payload: UpdateDocumentPayload) {
  return apiClient.patchJson<DocumentDetail, UpdateDocumentPayload>(`/api/v1/documents/${documentId}`, payload);
}

export function deleteDocument(documentId: string) {
  return apiClient.deleteJson<MutationResult>(`/api/v1/documents/${documentId}`);
}

export function downloadDocument(documentId: DownloadDocumentPathParams["document_id"]) {
  return apiClient.getBlob(`/api/v1/documents/${documentId}/download`);
}
