"""Spaces transport schemas for the Phase 3 identity migration phase."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


def normalize_space_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Space name must not be blank.")
    return normalized


class SpaceCreateRequest(BaseModel):
    name: str = Field(..., max_length=255, json_schema_extra={"example": "Architecture"})
    description: str | None = Field(default=None, json_schema_extra={"example": "ADR workspace"})

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return normalize_space_name(value)


class SpaceUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None)
    archived: bool | None = Field(default=None)
    is_default: bool | None = Field(default=None)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return normalize_space_name(value)


class SpaceResponse(BaseModel):
    id: UUID
    owner_user_id: UUID
    name: str
    description: str | None = None
    is_default: bool
    document_count: int = Field(ge=0)
    tracked_field_count: int = Field(ge=0)
    archived_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpaceListResponse(BaseModel):
    items: list[SpaceResponse]
