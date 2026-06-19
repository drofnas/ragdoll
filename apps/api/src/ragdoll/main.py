"""FastAPI application bootstrap for the clean-room rebuild."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ragdoll.api.errors import register_exception_handlers
from ragdoll.api.router import router as api_router
from ragdoll.core.config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Phase 1 placeholder lifespan hook for future runtime wiring."""
    app.state.runtime_bootstrap = "phase_1_scaffold"
    yield


def create_app() -> FastAPI:
    """Create the FastAPI application instance."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()
