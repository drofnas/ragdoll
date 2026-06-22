from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from ragdoll.api.shared_schemas import Citation, SourceTier


TrackedStateStatus = Literal["empty", "resolved", "conflict"]


class TrackedFieldCreateRequest(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    label: str = Field(min_length=1, max_length=255)
    prompt: str = Field(min_length=1)
    entity_type_hint: str | None = Field(default=None, max_length=80)
    is_active: bool = True


class TrackedFieldUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=255)
    prompt: str | None = Field(default=None, min_length=1)
    entity_type_hint: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None


class TrackedFieldDefinition(BaseModel):
    id: UUID
    space_id: UUID
    key: str
    label: str
    prompt: str
    entity_type_hint: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TrackedFieldDefinitionListResponse(BaseModel):
    items: list[TrackedFieldDefinition]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class TrackedValueCandidate(BaseModel):
    value_text: str
    source_tier: SourceTier
    correction_id: UUID | None = None
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime | None = None
    status: str


class TrackedFieldSummary(TrackedFieldDefinition):
    status: TrackedStateStatus
    current_value: str | None = None
    current_source_tier: SourceTier | None = None
    current_value_updated_at: datetime | None = None
    conflict_count: int = Field(default=0, ge=0)
    pending_correction_count: int = Field(default=0, ge=0)


class TrackedStateSummaryResponse(BaseModel):
    items: list[TrackedFieldSummary]


class TrackedStateConflict(BaseModel):
    field: TrackedFieldDefinition
    status: TrackedStateStatus
    candidates: list[TrackedValueCandidate] = Field(default_factory=list)


class TrackedStateConflictResponse(BaseModel):
    items: list[TrackedStateConflict]
