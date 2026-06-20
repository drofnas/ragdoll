from fastapi import APIRouter

from ragdoll.api.health import readiness_router
from ragdoll.modules.registry import V1_MODULE_REGISTRY


def build_v1_router() -> APIRouter:
    """Compose the versioned API router from the central module registry."""
    router = APIRouter()
    router.include_router(readiness_router)
    for module in V1_MODULE_REGISTRY:
        router.include_router(module.load_router())
    return router


router = build_v1_router()
