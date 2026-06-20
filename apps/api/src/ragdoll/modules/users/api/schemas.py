"""Users transport schemas used by auth-owned endpoints in the Phase 2A slice."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ragdoll.core.feature_flags import FeatureFlags, PlanTier
from ragdoll.modules.users.domain.policies import normalize_email_address


class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None = None
    is_active: bool
    is_admin: bool = False
    must_change_password: bool = False
    plan_tier: PlanTier = Field(default=PlanTier.FREE)
    feature_flags: FeatureFlags = Field(default_factory=dict)
    last_login: datetime | None = None

    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


class UpdateCurrentUserRequest(BaseModel):
    full_name: str | None = None
    email: str | None = None
    current_password: str | None = None
    new_password: str | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return normalize_email_address(value)
