"""Search transport schemas for Phase 9 retrieval reads."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from ragdoll.api.shared_schemas import Citation


class SearchMode(str, Enum):
    BOOLEAN = "boolean"
    VECTOR = "vector"
    GRAPH = "graph"
    COMBINED = "combined"


SearchResultKind = Literal["document_chunk", "entity"]


class SearchResultDocument(BaseModel):
    id: UUID
    space_id: UUID
    title: str
    file_type: str
    created_at: datetime


class SearchEntitySummary(BaseModel):
    id: UUID
    entity_type: str
    display_name: str
    normalized_name: str
    mention_count: int | None = Field(default=None, ge=0)


class SearchResult(BaseModel):
    result_id: str
    result_kind: SearchResultKind
    score: float
    matched_modes: list[SearchMode] = Field(default_factory=list)
    document: SearchResultDocument | None = None
    preview_text: str
    entity: SearchEntitySummary | None = None
    citations: list[Citation] = Field(default_factory=list)


class SearchResponse(BaseModel):
    items: list[SearchResult]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
