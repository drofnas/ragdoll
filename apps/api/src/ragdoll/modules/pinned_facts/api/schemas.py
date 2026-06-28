from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from ragdoll.api.shared_schemas import Citation


PinnedFactStatus = Literal["active", "pending_update", "conflicted", "unknown"]
PinnedFactValueKind = Literal["text", "json"]
PinnedFactCandidateChangeType = Literal["same", "update", "conflict", "unknown"]
PinnedFactCandidateStatus = Literal["pending", "accepted", "rejected", "auto_applied"]


class PinnedFactEvidence(BaseModel):
    quote: str = Field(min_length=1)
    citations: list[Citation] = Field(default_factory=list)
    source_chunk_ids: list[str] = Field(default_factory=list)


class PinnedFactValueMixin(BaseModel):
    value_kind: PinnedFactValueKind
    value_text: str | None = None
    value_json: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_value_shape(self) -> "PinnedFactValueMixin":
        if self.value_kind == "text":
            if not (self.value_text or "").strip():
                raise ValueError("value_text is required when value_kind='text'.")
            self.value_text = self.value_text.strip()
            self.value_json = None
        else:
            if self.value_json is None:
                raise ValueError("value_json is required when value_kind='json'.")
            self.value_text = None
        return self


class PinnedFactCreateRequest(PinnedFactValueMixin):
    key: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    entity_type_hint: str | None = Field(default=None, max_length=80)
    is_active: bool = True
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_document_id: UUID | None = None
    evidence: list[PinnedFactEvidence] = Field(min_length=1)


class PinnedFactUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    entity_type_hint: str | None = Field(default=None, max_length=80)
    is_active: bool | None = None


class PinnedFactSummary(BaseModel):
    id: UUID
    space_id: UUID
    key: str
    title: str
    description: str
    entity_type_hint: str | None = None
    is_active: bool
    status: PinnedFactStatus
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    value_kind: PinnedFactValueKind | None = None
    value_text: str | None = None
    value_json: dict[str, Any] | None = None
    source_document_id: UUID | None = None
    evidence: list[PinnedFactEvidence] = Field(default_factory=list)
    last_checked_at: datetime | None = None
    pending_candidate_count: int = Field(default=0, ge=0)
    conflict_count: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime


class PinnedFactDetail(PinnedFactSummary):
    history_count: int = Field(default=0, ge=0)


class PinnedFactListResponse(BaseModel):
    items: list[PinnedFactSummary]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class PinnedFactCandidate(BaseModel):
    id: UUID
    pinned_fact_id: UUID
    space_id: UUID
    source_document_id: UUID | None = None
    proposed_value_kind: PinnedFactValueKind
    proposed_value_text: str | None = None
    proposed_value_json: dict[str, Any] | None = None
    change_type: PinnedFactCandidateChangeType
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    evidence: list[PinnedFactEvidence] = Field(default_factory=list)
    status: PinnedFactCandidateStatus
    review_notes: str | None = None
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    created_at: datetime


class PinnedFactCandidateListResponse(BaseModel):
    items: list[PinnedFactCandidate]


class PinnedFactHistoryEntry(BaseModel):
    id: UUID
    pinned_fact_id: UUID
    candidate_id: UUID | None = None
    restored_from_history_id: UUID | None = None
    actor_user_id: UUID | None = None
    actor_type: str
    reason: str
    old_value_kind: PinnedFactValueKind | None = None
    old_value_text: str | None = None
    old_value_json: dict[str, Any] | None = None
    new_value_kind: PinnedFactValueKind
    new_value_text: str | None = None
    new_value_json: dict[str, Any] | None = None
    old_evidence: list[PinnedFactEvidence] = Field(default_factory=list)
    new_evidence: list[PinnedFactEvidence] = Field(default_factory=list)
    created_at: datetime


class PinnedFactHistoryResponse(BaseModel):
    items: list[PinnedFactHistoryEntry]


class AcceptPinnedFactCandidateRequest(BaseModel):
    value_kind: PinnedFactValueKind | None = None
    value_text: str | None = None
    value_json: dict[str, Any] | None = None
    review_notes: str | None = None

    @model_validator(mode="after")
    def validate_optional_value_shape(self) -> "AcceptPinnedFactCandidateRequest":
        if self.value_kind is None:
            self.value_text = None
            self.value_json = None
            return self
        if self.value_kind == "text":
            if not (self.value_text or "").strip():
                raise ValueError("value_text is required when overriding a candidate with text.")
            self.value_text = self.value_text.strip()
            self.value_json = None
        else:
            if self.value_json is None:
                raise ValueError("value_json is required when overriding a candidate with json.")
            self.value_text = None
        return self


class RejectPinnedFactCandidateRequest(BaseModel):
    review_notes: str | None = None
