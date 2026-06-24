import type {
  ChangeEventDetail,
  ChangeListResponse,
  ChatSessionDetail,
  ChatSessionListResponse,
  CorrectionListResponse,
  CorrectionRecordResponse,
  DocumentDetail,
  DocumentListResponse,
  DocumentProcessingStatusResponse,
  EntityDetailResponse,
  EntityListResponse,
  GraphResponse,
  ProcessingStatus,
  SearchResponse,
  SpaceListResponse,
  SpaceResponse,
  TrackedFieldDefinitionListResponse,
  TrackedStateConflictResponse,
  TrackedStateSummaryResponse,
  UsageSummaryResponse,
  UserProfileResponse
} from "@contracts";

export const userProfile: UserProfileResponse = {
  email: "user@example.com",
  full_name: "Test User",
  id: "11111111-1111-1111-1111-111111111111",
  is_active: true,
  is_admin: false,
  last_login: "2026-06-22T17:00:00Z",
  must_change_password: false
};

export const adminProfile: UserProfileResponse = {
  ...userProfile,
  email: "admin@example.com",
  full_name: "Admin User",
  id: "22222222-2222-2222-2222-222222222222",
  is_admin: true
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

export const searchResponse: SearchResponse = {
  items: [
    {
      citations: [
        {
          document_id: documentDetail.id,
          locator: "page 1",
          source_tier: "document",
          title: documentDetail.title
        }
      ],
      document: {
        created_at: documentDetail.created_at,
        file_type: documentDetail.file_type,
        id: documentDetail.id,
        space_id: documentDetail.space_id,
        title: documentDetail.title
      },
      entity: {
        display_name: "FastAPI",
        entity_type: "framework",
        id: "77777777-7777-7777-7777-777777777777",
        mention_count: 3,
        normalized_name: "fastapi"
      },
      matched_modes: ["combined", "vector"],
      preview_text: "FastAPI powers the backend runtime for the rebuilt product.",
      result_id: "search-result-1",
      result_kind: "document_chunk",
      score: 0.97
    }
  ],
  page: 1,
  page_size: 10,
  total: 1
};

export const chatSessionListResponse: ChatSessionListResponse = {
  items: [
    {
      created_at: "2026-06-22T17:10:00Z",
      document_id: documentDetail.id,
      id: "88888888-8888-8888-8888-888888888888",
      last_message_at: "2026-06-22T17:15:00Z",
      message_count: 2,
      space_id: spaces[0].id,
      title: "Architecture questions",
      updated_at: "2026-06-22T17:15:00Z"
    }
  ],
  page: 1,
  page_size: 25,
  total: 1
};

export const chatSessionDetail: ChatSessionDetail = {
  ...chatSessionListResponse.items[0],
  messages: [
    {
      content: "What backend framework does this repo use?",
      created_at: "2026-06-22T17:11:00Z",
      degraded: false,
      id: "99999999-9999-9999-9999-999999999999",
      role: "user"
    },
    {
      citations: [
        {
          document_id: documentDetail.id,
          locator: "page 1",
          source_tier: "document",
          title: documentDetail.title
        }
      ],
      content: "The backend uses FastAPI and exposes versioned routes under /api/v1.",
      created_at: "2026-06-22T17:12:00Z",
      degraded: true,
      id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
      retrieval_mode: "combined",
      role: "assistant",
      suggestions: [
        {
          label: "Follow up",
          prompt: "Show me where the FastAPI app boots."
        }
      ]
    }
  ]
};

export const entityListResponse: EntityListResponse = {
  items: [
    {
      created_at: "2026-06-22T17:00:00Z",
      display_name: "FastAPI",
      document_count: 1,
      entity_type: "framework",
      graph_node_id: "graph-fastapi",
      id: "77777777-7777-7777-7777-777777777777",
      latest_mentioned_at: "2026-06-22T17:05:00Z",
      mention_count: 3,
      normalized_name: "fastapi",
      space_id: spaces[0].id,
      updated_at: "2026-06-22T17:05:00Z"
    }
  ],
  page: 1,
  page_size: 12,
  total: 1
};

export const entityDetail: EntityDetailResponse = {
  ...entityListResponse.items[0],
  history: [
    {
      citation: {
        document_id: documentDetail.id,
        locator: "page 1",
        source_tier: "document",
        title: documentDetail.title
      },
      document_id: documentDetail.id,
      mention_id: "mention-history-1",
      observed_at: "2026-06-22T17:05:00Z",
      surface_text: "FastAPI"
    }
  ],
  provenance: [
    {
      citation: {
        chunk_id: "chunk-1",
        document_id: documentDetail.id,
        locator: "page 1",
        source_tier: "document",
        title: documentDetail.title
      },
      chunk_id: "chunk-1",
      confidence_score: 0.94,
      created_at: "2026-06-22T17:05:00Z",
      document_id: documentDetail.id,
      extraction_metadata: null,
      mention_id: "mention-1",
      normalized_name: "fastapi",
      surface_text: "FastAPI"
    }
  ],
  related_documents: [
    {
      citation: {
        document_id: documentDetail.id,
        locator: "page 1",
        source_tier: "document",
        title: documentDetail.title
      },
      document_id: documentDetail.id,
      file_type: documentDetail.file_type,
      latest_mentioned_at: "2026-06-22T17:05:00Z",
      mention_count: 3,
      title: documentDetail.title
    }
  ]
};

export const entityGraph: GraphResponse = {
  depth: 1,
  links: [
    {
      citations: [
        {
          document_id: documentDetail.id,
          locator: "page 1",
          source_tier: "derived",
          title: documentDetail.title
        }
      ],
      relation_type: "depends_on",
      source_id: "graph-fastapi",
      target_id: "graph-openapi",
      weight: 0.8
    }
  ],
  nodes: [
    {
      id: "graph-fastapi",
      label: "FastAPI",
      node_type: "framework",
      space_id: spaces[0].id
    },
    {
      id: "graph-openapi",
      label: "OpenAPI",
      node_type: "contract",
      space_id: spaces[0].id
    }
  ],
  seed_entity_id: entityDetail.id
};

export const trackedFieldDefinitions: TrackedFieldDefinitionListResponse = {
  items: [
    {
      created_at: "2026-06-22T17:00:00Z",
      entity_type_hint: "framework",
      id: "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
      is_active: true,
      key: "current_backend_framework",
      label: "Current backend framework",
      prompt: "What backend framework powers this repo today?",
      space_id: spaces[0].id,
      updated_at: "2026-06-22T17:05:00Z"
    }
  ],
  page: 1,
  page_size: 50,
  total: 1
};

export const trackedStateSummary: TrackedStateSummaryResponse = {
  items: [
    {
      ...trackedFieldDefinitions.items[0],
      conflict_count: 1,
      current_source_tier: "verified",
      current_value: "FastAPI",
      current_value_updated_at: "2026-06-22T17:06:00Z",
      pending_correction_count: 1,
      status: "resolved"
    }
  ]
};

export const trackedStateConflicts: TrackedStateConflictResponse = {
  items: [
    {
      candidates: [
        {
          citations: [
            {
              document_id: documentDetail.id,
              locator: "page 1",
              source_tier: "document",
              title: documentDetail.title
            }
          ],
          created_at: "2026-06-22T17:06:00Z",
          source_tier: "document",
          status: "candidate",
          value_text: "FastAPI"
        },
        {
          citations: [
            {
              document_id: documentDetail.id,
              locator: "page 2",
              source_tier: "document",
              title: documentDetail.title
            }
          ],
          created_at: "2026-06-22T17:07:00Z",
          source_tier: "document",
          status: "candidate",
          value_text: "Starlette"
        }
      ],
      field: trackedFieldDefinitions.items[0],
      status: "conflict"
    }
  ]
};

export const changeListResponse: ChangeListResponse = {
  items: [
    {
      chat_session_id: chatSessionDetail.id,
      correction_id: null,
      created_at: "2026-06-22T17:16:00Z",
      document_id: documentDetail.id,
      event_type: "chat_answered",
      id: "cccccccc-cccc-cccc-cccc-cccccccccccc",
      is_read: false,
      space_id: spaces[0].id,
      summary: "A retrieval-backed answer cited the implementation plan.",
      title: "Chat answer generated",
      tracked_field_id: null
    }
  ],
  page: 1,
  page_size: 10,
  total: 1
};

export const changeDetail: ChangeEventDetail = {
  ...changeListResponse.items[0],
  payload: {
    session_id: chatSessionDetail.id
  }
};

export const correctionDetail: CorrectionRecordResponse = {
  chat_message_id: "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
  chat_session_id: chatSessionDetail.id,
  citation: {
    document_id: documentDetail.id,
    locator: "page 1",
    source_tier: "document",
    title: documentDetail.title
  },
  created_at: "2026-06-22T17:17:00Z",
  document_id: documentDetail.id,
  entity_id: entityDetail.id,
  id: "dddddddd-dddd-dddd-dddd-dddddddddddd",
  locator_text: "page 1",
  proposed_value: "The repo uses FastAPI for the API service.",
  rationale: "The answer should mention the API service explicitly.",
  review_notes: null,
  reviewed_at: null,
  reviewed_by: null,
  space_id: spaces[0].id,
  status: "pending",
  submitted_by: userProfile.id,
  tracked_field_id: trackedFieldDefinitions.items[0].id,
  updated_at: "2026-06-22T17:17:00Z"
};

export const correctionListResponse: CorrectionListResponse = {
  items: [correctionDetail],
  page: 1,
  page_size: 10,
  total: 1
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
