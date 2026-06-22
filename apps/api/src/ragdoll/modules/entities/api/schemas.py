"""Entities transport schemas for Phase 9 retrieval reads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ragdoll.api.shared_schemas import Citation


class EntityListItem(BaseModel):
    id: UUID
    space_id: UUID
    entity_type: str
    display_name: str
    normalized_name: str
    graph_node_id: UUID | None = None
    mention_count: int = Field(ge=0)
    document_count: int = Field(ge=0)
    latest_mentioned_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class EntityMentionRecord(BaseModel):
    mention_id: UUID
    document_id: UUID
    chunk_id: UUID
    surface_text: str
    normalized_name: str
    confidence_score: float | None = None
    extraction_metadata: dict[str, object] | None = None
    created_at: datetime
    citation: Citation


class EntityHistoryEntry(BaseModel):
    mention_id: UUID
    document_id: UUID
    surface_text: str
    observed_at: datetime
    citation: Citation


class EntityRelatedDocument(BaseModel):
    document_id: UUID
    title: str
    file_type: str
    mention_count: int = Field(ge=0)
    latest_mentioned_at: datetime | None = None
    citation: Citation | None = None


class EntityDetailResponse(EntityListItem):
    provenance: list[EntityMentionRecord] = Field(default_factory=list)
    history: list[EntityHistoryEntry] = Field(default_factory=list)
    related_documents: list[EntityRelatedDocument] = Field(default_factory=list)


class EntityListResponse(BaseModel):
    items: list[EntityListItem]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
