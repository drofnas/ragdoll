from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ragdoll.api.shared_schemas import Citation, SourceTier


class CorrectionCreateRequest(BaseModel):
    tracked_field_id: UUID | None = None
    chat_session_id: UUID | None = None
    chat_message_id: UUID | None = None
    document_id: UUID | None = None
    entity_id: UUID | None = None
    locator_text: str | None = None
    proposed_value: str = Field(min_length=1)
    rationale: str | None = None


class CorrectionReviewRequest(BaseModel):
    review_notes: str | None = None


class CorrectionRecordResponse(BaseModel):
    id: UUID
    space_id: UUID
    submitted_by: UUID
    chat_session_id: UUID | None = None
    chat_message_id: UUID | None = None
    tracked_field_id: UUID | None = None
    document_id: UUID | None = None
    entity_id: UUID | None = None
    locator_text: str | None = None
    proposed_value: str
    rationale: str | None = None
    status: str
    review_notes: str | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    citation: Citation


class CorrectionListResponse(BaseModel):
    items: list[CorrectionRecordResponse]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
