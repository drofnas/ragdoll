from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ChangeEventSummary(BaseModel):
    id: UUID
    space_id: UUID
    event_type: str
    title: str
    summary: str
    document_id: UUID | None = None
    pinned_fact_id: UUID | None = None
    correction_id: UUID | None = None
    chat_session_id: UUID | None = None
    created_at: datetime
    is_read: bool = False


class ChangeEventDetail(ChangeEventSummary):
    payload: dict[str, Any] | None = None


class ChangeListResponse(BaseModel):
    items: list[ChangeEventSummary]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class ChangeEventReadResult(BaseModel):
    change_event_id: UUID
    read_at: datetime
