from pydantic import BaseModel, ConfigDict, Field
from fastapi import APIRouter

PHASE_1_NOT_CONFIGURED_DETAIL = "Phase 1 scaffold: probe not wired yet"
DEPENDENCY_KEYS = ("database", "storage", "vector", "graph", "llm", "queue")


class LivenessResponse(BaseModel):
    status: str = Field(default="ok")

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})


class DependencyStatus(BaseModel):
    status: str = Field(default="not_configured")
    detail: str = Field(default=PHASE_1_NOT_CONFIGURED_DETAIL)


class ReadinessResponse(BaseModel):
    status: str = Field(default="degraded")
    services: dict[str, DependencyStatus]


def build_readiness_payload() -> ReadinessResponse:
    return ReadinessResponse(
        status="degraded",
        services={
            key: DependencyStatus(status="not_configured", detail=PHASE_1_NOT_CONFIGURED_DETAIL)
            for key in DEPENDENCY_KEYS
        },
    )


liveness_router = APIRouter()
readiness_router = APIRouter()


@liveness_router.get("/health", response_model=LivenessResponse, tags=["health"])
async def health_liveness() -> LivenessResponse:
    return LivenessResponse(status="ok")


@readiness_router.get("/health", response_model=ReadinessResponse, tags=["health"])
async def health_readiness() -> ReadinessResponse:
    return build_readiness_payload()
