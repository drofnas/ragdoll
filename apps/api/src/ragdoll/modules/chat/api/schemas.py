from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from ragdoll.api.shared_schemas import Citation


class ChatSuggestion(BaseModel):
    label: str
    prompt: str


class ChatMessageRecord(BaseModel):
    id: UUID
    role: str
    content: str
    citations: list[Citation] = Field(default_factory=list)
    suggestions: list[ChatSuggestion] = Field(default_factory=list)
    retrieval_mode: str | None = None
    degraded: bool = False
    created_at: datetime


class ChatSessionSummary(BaseModel):
    id: UUID
    space_id: UUID
    title: str
    message_count: int = Field(ge=0)
    last_message_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ChatSessionDetail(ChatSessionSummary):
    messages: list[ChatMessageRecord] = Field(default_factory=list)


class ChatSendMessageRequest(BaseModel):
    content: str = Field(min_length=1)


class ChatSendMessageResponse(BaseModel):
    session: ChatSessionDetail
    user_message: ChatMessageRecord
    assistant_message: ChatMessageRecord


class ChatSessionListResponse(BaseModel):
    items: list[ChatSessionSummary]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
