"""Documents transport schemas for the document-library migration slice."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ragdoll.api.shared_schemas import ProcessingStatus


SourceKind = Literal["manual_upload", "external_sync"]


class DocumentListItem(BaseModel):
    id: UUID
    space_id: UUID
    uploaded_by: UUID
    title: str
    original_filename: str
    mime_type: str
    file_type: str
    file_size: int = Field(ge=0)
    source_kind: SourceKind
    source_label: str | None = None
    processing_status: ProcessingStatus
    chunk_count: int = Field(ge=0)
    indexed_chunk_count: int = Field(ge=0)
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetail(DocumentListItem):
    preview_text: str | None = None
    original_text_content: str | None = None


class DocumentUpdateRequest(BaseModel):
    space_id: UUID


class DocumentListResponse(BaseModel):
    items: list[DocumentListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
