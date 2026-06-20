from __future__ import annotations

import httpx
from fastapi import APIRouter
from sqlalchemy import text

from ragdoll.api.shared_schemas import DependencyStatus, HealthStatusResponse
from ragdoll.core.config import Settings, get_settings
from ragdoll.platform.db.engine import get_engine

PHASE_1_NOT_CONFIGURED_DETAIL = "Phase 1 scaffold: probe not wired yet"
DEPENDENCY_KEYS = ("database", "storage", "vector", "graph", "llm", "queue")

from pydantic import BaseModel, ConfigDict, Field


class LivenessResponse(BaseModel):
    status: str = Field(default="ok")

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})


def _service(status: str, detail: str, *, backend: str | None = None) -> DependencyStatus:
    return DependencyStatus(status=status, detail=detail, backend=backend)


def _check_database(settings: Settings) -> DependencyStatus:
    if not settings.has_database_config:
        return _service("not_configured", "Database URL is not configured yet.")
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return _service("healthy", "Database connection is ready.")
    except Exception as exc:
        return _service("unhealthy", f"Database probe failed: {exc}")


def _check_storage(settings: Settings) -> DependencyStatus:
    if not settings.has_storage_config:
        return _service("not_configured", "Supabase storage settings are incomplete.", backend="supabase")

    url = (settings.supabase_url or "").rstrip("/")
    headers = {
        "authorization": f"Bearer {(settings.supabase_service_role_key or '').strip()}",
        "apikey": (settings.supabase_service_role_key or "").strip(),
    }
    try:
        response = httpx.get(f"{url}/storage/v1/bucket", headers=headers, timeout=5.0)
        response.raise_for_status()
        buckets = response.json()
        bucket_name = settings.effective_storage_bucket
        found = any(
            (
                (item.get("name") or item.get("id"))
                if isinstance(item, dict)
                else None
            )
            == bucket_name
            for item in (buckets or [])
        )
        if not found:
            return _service(
                "not_configured",
                f"Supabase storage bucket '{bucket_name}' was not found.",
                backend="supabase",
            )
        return _service("healthy", "Supabase storage bucket is reachable.", backend="supabase")
    except Exception as exc:
        return _service("unhealthy", f"Storage probe failed: {exc}", backend="supabase")


def _check_vector(settings: Settings) -> DependencyStatus:
    if not settings.has_database_config:
        return _service("not_configured", "Database URL is required before vector readiness can be checked.", backend="supabase")
    try:
        with get_engine().connect() as connection:
            row = connection.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).first()
        if row is None:
            return _service("not_configured", "pgvector extension is not installed.", backend="supabase")
        return _service("healthy", "pgvector extension is installed.", backend="supabase")
    except Exception as exc:
        return _service("unhealthy", f"Vector probe failed: {exc}", backend="supabase")


def _check_graph(settings: Settings, database_status: DependencyStatus) -> DependencyStatus:
    if settings.e2e_memory_backends:
        return _service("healthy", "In-memory graph backend is enabled.", backend="memory")
    if not settings.has_database_config:
        return _service("not_configured", "Database URL is required before graph readiness can be checked.", backend="supabase")
    if database_status.status != "healthy":
        return _service("unhealthy", "Graph backing prerequisites depend on a healthy database connection.", backend="supabase")
    return _service(
        "healthy",
        "Graph backing prerequisites are available through the configured relational backend.",
        backend="supabase",
    )


def _check_queue() -> DependencyStatus:
    return _service("not_configured", "Queue runtime is deferred until a later phase.")


async def _check_llm(settings: Settings) -> DependencyStatus:
    base_url = (settings.ollama_base_url or "").rstrip("/")
    if not base_url:
        return _service("not_configured", "OLLAMA_BASE_URL is not configured.")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
        if not isinstance(payload.get("models"), list):
            return _service("unhealthy", "Ollama /api/tags returned an unexpected payload.")
        return _service("healthy", "Ollama model catalog is reachable.")
    except Exception as exc:
        return _service("unhealthy", f"Ollama probe failed: {exc}")


async def build_readiness_payload(settings: Settings | None = None) -> HealthStatusResponse:
    runtime_settings = settings or get_settings()
    database_status = _check_database(runtime_settings)
    services = {
        "database": database_status,
        "storage": _check_storage(runtime_settings),
        "vector": _check_vector(runtime_settings),
        "graph": _check_graph(runtime_settings, database_status),
        "llm": await _check_llm(runtime_settings),
        "queue": _check_queue(),
    }
    overall_status = "ok" if all(service.status == "healthy" for service in services.values()) else "degraded"
    return HealthStatusResponse(status=overall_status, services=services)


liveness_router = APIRouter()
readiness_router = APIRouter()


@liveness_router.get("/health", response_model=LivenessResponse, tags=["health"])
async def health_liveness() -> LivenessResponse:
    return LivenessResponse(status="ok")


@readiness_router.get("/health", response_model=HealthStatusResponse, tags=["health"])
async def health_readiness() -> HealthStatusResponse:
    return await build_readiness_payload()
