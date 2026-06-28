from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from ragdoll.api.shared_schemas import PaginatedResponse


class AdminManagedUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str | None = None
    is_active: bool
    is_admin: bool
    must_change_password: bool
    last_login: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AdminManagedUserListResponse(PaginatedResponse[AdminManagedUserResponse]):
    pass


class AdminUpdateUserRequest(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    must_change_password: bool | None = None


class AdminEffectiveLimitsResponse(BaseModel):
    documents: int | None = None
    max_file_size_bytes: int | None = None
    chunks: int | None = None
    storage_bytes: int | None = None
    tokens_5h: int | None = None
    tokens_week: int | None = None
    retrieval_chunks: int
    output_tokens: int
    per_document_chunks: int
