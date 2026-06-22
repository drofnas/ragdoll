"""Knowledge graph transport schemas for Phase 9 retrieval reads."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from ragdoll.api.shared_schemas import Citation


class GraphNodeResponse(BaseModel):
    id: UUID
    space_id: UUID
    label: str
    node_type: str


class GraphLinkResponse(BaseModel):
    source_id: UUID
    target_id: UUID
    relation_type: str
    weight: float
    citations: list[Citation] = Field(default_factory=list)


class GraphResponse(BaseModel):
    seed_entity_id: UUID | None = None
    document_id: UUID | None = None
    depth: int = Field(ge=1)
    nodes: list[GraphNodeResponse] = Field(default_factory=list)
    links: list[GraphLinkResponse] = Field(default_factory=list)
