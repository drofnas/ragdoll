"""Shared public transport schemas for the versioned API surface."""

from __future__ import annotations

from enum import Enum
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, RootModel, model_validator

from ragdoll.core.feature_flags import PlanTier


T = TypeVar("T")


class ProblemResponse(BaseModel):
    """Stable problem+json response body."""

    type: str = Field(default="https://ragdoll.dev/problems/http-error")
    title: str = Field(default="HTTP request failed")
    status: int = Field(..., ge=100, le=599)
    detail: str = Field(...)
    instance: str = Field(default="about:blank")
    code: str | None = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "https://ragdoll.dev/problems/authentication-required",
                "title": "Authentication required",
                "status": 401,
                "detail": "Authentication credentials are required for this resource.",
                "instance": "/api/v1/spaces",
                "code": "authentication_required",
            }
        }
    )


class MutationResult(BaseModel):
    """Generic mutation response envelope."""

    success: bool = Field(default=True)
    message: str | None = Field(default=None)

    model_config = ConfigDict(
        json_schema_extra={"example": {"success": True, "message": "Updated successfully."}}
    )


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic page envelope."""

    items: list[T]
    total: int = Field(..., ge=0)
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)


class FeatureFlags(RootModel[dict[str, bool]]):
    """Resolved feature-flag map exposed to clients."""

    root: dict[str, bool] = Field(default_factory=dict)


class SourceTier(str, Enum):
    """Provenance tier for user-facing citations and history surfaces."""

    DOCUMENT = "document"
    DERIVED = "derived"
    USER = "user"
    VERIFIED = "verified"


class ProcessingStageStatus(str, Enum):
    """Normalized processing stage status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ProcessingStatus(BaseModel):
    """Stage-aware processing status contract."""

    overall: ProcessingStageStatus = Field(default=ProcessingStageStatus.PENDING)
    upload: ProcessingStageStatus = Field(default=ProcessingStageStatus.PENDING)
    parsing: ProcessingStageStatus = Field(default=ProcessingStageStatus.PENDING)
    vector: ProcessingStageStatus = Field(default=ProcessingStageStatus.PENDING)
    extraction: ProcessingStageStatus = Field(default=ProcessingStageStatus.PENDING)
    graph: ProcessingStageStatus = Field(default=ProcessingStageStatus.PENDING)
    detail: str | None = Field(default=None)


class SpaceScope(BaseModel):
    """Normalized future scope contract for Space-aware endpoints."""

    space_id: UUID | None = Field(default=None)
    all_spaces: bool = Field(default=False)

    @model_validator(mode="after")
    def validate_scope(self) -> "SpaceScope":
        if self.space_id is not None and self.all_spaces:
            raise ValueError("space_id and all_spaces=true cannot be used together.")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"space_id": "123e4567-e89b-12d3-a456-426614174000", "all_spaces": False}
        }
    )


class Citation(BaseModel):
    """User-facing citation payload."""

    document_id: UUID | None = Field(default=None)
    entity_id: UUID | None = Field(default=None)
    chunk_id: str | None = Field(default=None)
    title: str | None = Field(default=None)
    locator: str | None = Field(default=None)
    source_tier: SourceTier = Field(default=SourceTier.DOCUMENT)


class DependencyStatus(BaseModel):
    """Readiness status for one dependency."""

    status: str = Field(default="not_configured")
    detail: str = Field(default="Not configured.")
    backend: str | None = Field(default=None)


class HealthStatusResponse(BaseModel):
    """Aggregated readiness response."""

    status: str = Field(default="degraded")
    services: dict[str, DependencyStatus]


__all__ = [
    "Citation",
    "DependencyStatus",
    "FeatureFlags",
    "HealthStatusResponse",
    "MutationResult",
    "PaginatedResponse",
    "PlanTier",
    "ProblemResponse",
    "ProcessingStageStatus",
    "ProcessingStatus",
    "SourceTier",
    "SpaceScope",
]
