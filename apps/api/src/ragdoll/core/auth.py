from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from ragdoll.core.exceptions import AuthenticationRequiredError
from ragdoll.core.feature_flags import FeatureFlags, PlanTier
from ragdoll.core.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedPrincipal(BaseModel):
    subject: str = Field(..., json_schema_extra={"example": "user-123"})
    email: str | None = Field(default=None, json_schema_extra={"example": "user@example.com"})
    is_admin: bool = Field(default=False)
    plan_tier: PlanTier = Field(default=PlanTier.FREE)
    feature_flags: FeatureFlags = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=True)


def get_bearer_token_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    if credentials is None:
        return None
    return credentials.credentials


def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise AuthenticationRequiredError("Authentication token is required.")
    return credentials.credentials


def decode_principal_from_token(token: str) -> dict[str, Any]:
    return decode_access_token(token)
