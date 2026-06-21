"""Auth transport schemas for the Phase 3 identity migration phase."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ragdoll.modules.users.domain.policies import normalize_email_address


class RegisterRequest(BaseModel):
    email: str = Field(..., json_schema_extra={"example": "user@example.com"})
    password: str = Field(..., min_length=8, json_schema_extra={"example": "testpass123"})
    full_name: str | None = Field(default=None, json_schema_extra={"example": "Ada Lovelace"})

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email_address(value)


class LoginTokenResponse(BaseModel):
    access_token: str = Field(..., json_schema_extra={"example": "eyJhbGciOiJIUzI1NiJ9..."})
    token_type: str = Field(default="bearer", json_schema_extra={"example": "bearer"})
    must_change_password: bool = Field(default=False)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiJ9...",
                "token_type": "bearer",
                "must_change_password": False,
            }
        }
    )
