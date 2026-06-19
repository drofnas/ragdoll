from fastapi import APIRouter

from ragdoll.api.health import liveness_router
from ragdoll.api.v1.router import router as v1_router

router = APIRouter()
router.include_router(liveness_router)
router.include_router(v1_router, prefix="/api/v1")
