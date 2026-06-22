import type {
  DocumentDetail,
  DocumentListResponse,
  DocumentProcessingStatusResponse,
  ProcessingStatus,
  SpaceListResponse,
  SpaceResponse,
  UsageSummaryResponse,
  UserProfileResponse
} from "@contracts";

export const userProfile: UserProfileResponse = {
  email: "user@example.com",
  feature_flags: {
    unified_search: true
  },
  full_name: "Test User",
  id: "11111111-1111-1111-1111-111111111111",
  is_active: true,
  is_admin: false,
  last_login: "2026-06-22T17:00:00Z",
  must_change_password: false,
  plan_tier: "free"
};

export const adminProfile: UserProfileResponse = {
  ...userProfile,
  email: "admin@example.com",
  full_name: "Admin User",
  id: "22222222-2222-2222-2222-222222222222",
  is_admin: true,
  plan_tier: "internal"
};

export const spaces: SpaceResponse[] = [
  {
    archived_at: null,
    created_at: "2026-06-22T17:00:00Z",
    description: "Primary workspace",
    id: "33333333-3333-3333-3333-333333333333",
    is_default: true,
    name: "Core Space",
    owner_user_id: userProfile.id,
    updated_at: "2026-06-22T17:00:00Z"
  },
  {
    archived_at: null,
    created_at: "2026-06-22T17:00:00Z",
    description: "Secondary workspace",
    id: "44444444-4444-4444-4444-444444444444",
    is_default: false,
    name: "Archive Prep",
    owner_user_id: userProfile.id,
    updated_at: "2026-06-22T17:00:00Z"
  }
];

export const spaceListResponse: SpaceListResponse = {
  items: spaces
};

export const processingStatus: ProcessingStatus = {
  detail: null,
  extraction: "deferred",
  graph: "deferred",
  overall: "completed",
  parsing: "completed",
  upload: "completed",
  vector: "deferred"
};

export const documentDetail: DocumentDetail = {
  chunk_count: 6,
  created_at: "2026-06-22T17:00:00Z",
  file_size: 1024,
  file_type: "pdf",
  id: "55555555-5555-5555-5555-555555555555",
  indexed_chunk_count: 6,
  mime_type: "application/pdf",
  original_filename: "plan.pdf",
  original_text_content: "Full extracted document text",
  preview_text: "Preview text",
  processing_status: processingStatus,
  source_kind: "manual_upload",
  source_label: null,
  space_id: spaces[0].id,
  title: "Implementation Plan",
  updated_at: "2026-06-22T17:05:00Z",
  uploaded_by: userProfile.id
};

export const documentListResponse: DocumentListResponse = {
  items: [documentDetail],
  page: 1,
  page_size: 12,
  total: 1
};

export const documentStatusResponse: DocumentProcessingStatusResponse = {
  chunk_count: 6,
  document_id: documentDetail.id,
  indexed_chunk_count: 6,
  latest_job: {
    attempt: 1,
    completed_at: "2026-06-22T17:04:00Z",
    id: "66666666-6666-6666-6666-666666666666",
    queued_at: "2026-06-22T17:01:00Z",
    requested_stage: "parsing",
    started_at: "2026-06-22T17:02:00Z",
    status: "completed",
    visible_error_detail: null
  },
  processing_status: processingStatus,
  space_id: spaces[0].id,
  updated_at: "2026-06-22T17:05:00Z",
  uploaded_by: userProfile.id
};

export const usageSummary: UsageSummaryResponse = {
  limits: {
    chunks: 1000,
    documents: 50,
    max_file_size_bytes: 10000000,
    output_tokens: 0,
    per_document_chunks: 200,
    retrieval_chunks: 20,
    storage_bytes: 5000000,
    tokens_5h: 0,
    tokens_week: 0
  },
  percent_used: {
    chunks: 0.6,
    documents: 0.02,
    storage_bytes: 0.01,
    tokens_5h: null,
    tokens_week: null
  },
  plan_tier: "free",
  resets_at: {
    tokens_5h_resets_at: null,
    tokens_week_resets_at: null
  },
  status: {
    chat_blocked: false,
    partially_indexed_documents: 0,
    upload_blocked: false
  },
  usage: {
    chunks: 6,
    documents: 1,
    storage_bytes: 1024,
    tokens_5h: 0,
    tokens_week: 0
  }
};

export function jsonResponse(body: unknown, init?: ResponseInit) {
  return Promise.resolve(
    new Response(JSON.stringify(body), {
      headers: {
        "Content-Type": "application/json"
      },
      ...init
    })
  );
}
