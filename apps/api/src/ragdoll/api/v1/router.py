from fastapi import APIRouter

from ragdoll.api.health import readiness_router

router = APIRouter()
router.include_router(readiness_router)
