from __future__ import annotations

from datetime import datetime, timezone
from html import escape
import httpx
from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import text

from ragdoll.api.shared_schemas import (
    DependencyStatus,
    HealthStatusResponse,
    OllamaConfiguredModelStatus,
    RuntimeApplicationStatus,
    RuntimeOllamaStatus,
    RuntimeStatusResponse,
    RuntimeSupabaseStatus,
)
from ragdoll.core.config import Settings, get_settings
from ragdoll.platform.db.engine import get_engine

PHASE_1_NOT_CONFIGURED_DETAIL = "Phase 1 scaffold: probe not wired yet"
DEPENDENCY_KEYS = ("database", "storage", "vector", "graph", "llm", "queue")
APP_VERSION = "0.1.0"

from pydantic import BaseModel, ConfigDict, Field


class LivenessResponse(BaseModel):
    status: str = Field(default="ok")

    model_config = ConfigDict(json_schema_extra={"example": {"status": "ok"}})


def _service(status: str, detail: str, *, backend: str | None = None) -> DependencyStatus:
    return DependencyStatus(status=status, detail=detail, backend=backend)


def _redact_exception(service_name: str) -> str:
    return f"{service_name} probe failed."


def _check_database(settings: Settings) -> DependencyStatus:
    if not settings.has_database_config:
        return _service("not_configured", "Database URL is not configured yet.")
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return _service("healthy", "Database connection is ready.")
    except Exception as exc:
        return _service("unhealthy", f"Database probe failed: {exc}")


def _check_database_redacted(settings: Settings) -> DependencyStatus:
    if not settings.has_database_config:
        return _service("not_configured", "Database URL is not configured yet.")
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return _service("healthy", "Database connection is ready.")
    except Exception:
        return _service("unhealthy", _redact_exception("Database"))


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


def _check_storage_redacted(settings: Settings) -> DependencyStatus:
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
    except Exception:
        return _service("unhealthy", _redact_exception("Storage"), backend="supabase")


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


def _check_vector_redacted(settings: Settings) -> DependencyStatus:
    if not settings.has_database_config:
        return _service("not_configured", "Database URL is required before vector readiness can be checked.", backend="supabase")
    try:
        with get_engine().connect() as connection:
            row = connection.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).first()
        if row is None:
            return _service("not_configured", "pgvector extension is not installed.", backend="supabase")
        return _service("healthy", "pgvector extension is installed.", backend="supabase")
    except Exception:
        return _service("unhealthy", _redact_exception("Vector"), backend="supabase")


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


def _check_queue(settings: Settings, database_status: DependencyStatus) -> DependencyStatus:
    if settings.e2e_memory_backends:
        return _service("healthy", "In-memory queue backend is enabled.", backend="memory")
    if not settings.has_database_config:
        return _service("not_configured", "Database URL is required before queue readiness can be checked.", backend="sql")
    if database_status.status != "healthy":
        return _service("unhealthy", "Queue backing prerequisites depend on a healthy database connection.", backend="sql")
    return _service("healthy", "Database-backed queue runtime is available.", backend="sql")


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


async def _fetch_ollama_catalog(settings: Settings) -> tuple[DependencyStatus, set[str]]:
    base_url = (settings.ollama_base_url or "").rstrip("/")
    if not base_url:
        return _service("not_configured", "OLLAMA_BASE_URL is not configured."), set()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            response.raise_for_status()
            payload = response.json()
        models = payload.get("models")
        if not isinstance(models, list):
            return _service("unhealthy", "Ollama /api/tags returned an unexpected payload."), set()
        discovered: set[str] = set()
        for item in models:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if isinstance(name, str) and name.strip():
                discovered.add(name.strip())
        return _service("healthy", "Ollama model catalog is reachable."), discovered
    except Exception:
        return _service("unhealthy", _redact_exception("Ollama")), set()


def _runtime_generated_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_supabase_rollup(services: dict[str, DependencyStatus]) -> RuntimeSupabaseStatus:
    supabase_services = {
        key: services[key]
        for key in ("database", "storage", "vector", "graph")
    }
    statuses = {service.status for service in supabase_services.values()}

    if all(status == "healthy" for status in statuses):
        status = "healthy"
        detail = "Supabase-backed runtime dependencies are healthy."
    elif "unhealthy" in statuses:
        status = "unhealthy"
        detail = "One or more Supabase-backed runtime dependencies are unhealthy."
    elif all(status == "not_configured" for status in statuses):
        status = "not_configured"
        detail = "Supabase-backed runtime dependencies are not configured yet."
    else:
        status = "degraded"
        detail = "Supabase-backed runtime dependencies are only partially configured."

    return RuntimeSupabaseStatus(
        status=status,
        backend="supabase",
        detail=detail,
        services=supabase_services,
    )


def _configured_ollama_models(settings: Settings) -> list[tuple[str, str]]:
    return [
        ("primary_chat", settings.ollama_model.strip()),
        ("orchestrator", settings.ollama_orchestrator_model_effective.strip()),
        ("worker", settings.ollama_worker_model_effective.strip()),
        ("embedding", settings.ollama_embedding_model.strip()),
    ]


def _model_is_available(model_name: str, available_models: set[str]) -> bool:
    normalized = model_name.strip()
    if not normalized:
        return False
    if normalized in available_models:
        return True
    if normalized.endswith(":latest") and normalized[: -len(":latest")] in available_models:
        return True
    if f"{normalized}:latest" in available_models:
        return True
    return False


def _build_ollama_model_inventory(
    settings: Settings,
    llm_status: DependencyStatus,
    available_models: set[str],
) -> list[OllamaConfiguredModelStatus]:
    grouped: dict[str, dict[str, list[str] | str | None]] = {}
    missing_role_count = 0

    for role, model_name in _configured_ollama_models(settings):
        if not model_name:
            missing_role_count += 1
            grouped[f"__missing__:{role}"] = {
                "name": None,
                "roles": [role],
                "status": "not_configured",
                "detail": f"Ollama model for role '{role}' is not configured.",
            }
            continue

        entry = grouped.setdefault(
            model_name,
            {"name": model_name, "roles": [], "status": "unknown", "detail": "Model presence could not be determined."},
        )
        entry["roles"].append(role)

    models: list[OllamaConfiguredModelStatus] = []
    for key, entry in grouped.items():
        if key.startswith("__missing__:"):
            models.append(
                OllamaConfiguredModelStatus(
                    name=None,
                    roles=list(entry["roles"]),
                    status=str(entry["status"]),
                    detail=str(entry["detail"]),
                )
            )
            continue

        model_name = str(entry["name"])
        if llm_status.status == "not_configured":
            status = "not_configured"
            detail = "OLLAMA_BASE_URL is not configured."
        elif llm_status.status != "healthy":
            status = "unknown"
            detail = "Ollama model catalog could not be queried."
        elif _model_is_available(model_name, available_models):
            status = "present"
            detail = "Configured model is available in the Ollama catalog."
        else:
            status = "missing"
            detail = "Configured model was not found in the Ollama catalog."

        models.append(
            OllamaConfiguredModelStatus(
                name=model_name,
                roles=list(entry["roles"]),
                status=status,
                detail=detail,
            )
        )

    if not models and missing_role_count == 0:
        models.append(
            OllamaConfiguredModelStatus(
                name=None,
                roles=[],
                status="not_configured",
                detail="No Ollama models are configured.",
            )
        )
    return models


def _build_ollama_status(
    settings: Settings,
    llm_status: DependencyStatus,
    available_models: set[str],
) -> RuntimeOllamaStatus:
    return RuntimeOllamaStatus(
        status=llm_status.status,
        detail=llm_status.detail,
        configured_base_url=bool((settings.ollama_base_url or "").strip()),
        catalog_reachable=llm_status.status == "healthy",
        configured_models=_build_ollama_model_inventory(settings, llm_status, available_models),
    )


async def build_runtime_status_payload(
    settings: Settings | None = None,
    *,
    app_version: str = APP_VERSION,
) -> RuntimeStatusResponse:
    runtime_settings = settings or get_settings()
    database_status = _check_database_redacted(runtime_settings)
    services = {
        "database": database_status,
        "storage": _check_storage_redacted(runtime_settings),
        "vector": _check_vector_redacted(runtime_settings),
        "graph": _check_graph(runtime_settings, database_status),
        "queue": _check_queue(runtime_settings, database_status),
    }
    llm_status, available_models = await _fetch_ollama_catalog(runtime_settings)
    services["llm"] = llm_status
    overall_status = "ok" if all(service.status == "healthy" for service in services.values()) else "degraded"
    return RuntimeStatusResponse(
        status=overall_status,
        application=RuntimeApplicationStatus(
            name=runtime_settings.app_name,
            environment=runtime_settings.app_env,
            version=app_version,
            generated_at=_runtime_generated_at(),
        ),
        services=services,
        supabase=_build_supabase_rollup(services),
        ollama=_build_ollama_status(runtime_settings, llm_status, available_models),
    )


def _status_badge(status: str) -> str:
    palette = {
        "healthy": "#1f7a4d",
        "ok": "#1f7a4d",
        "degraded": "#b77200",
        "unhealthy": "#b42318",
        "not_configured": "#6b7280",
        "present": "#1f7a4d",
        "missing": "#b42318",
        "unknown": "#6b7280",
    }
    color = palette.get(status, "#6b7280")
    label = status.replace("_", " ")
    return (
        f"<span style=\"display:inline-block;padding:0.2rem 0.55rem;border-radius:999px;"
        f"background:{color}18;color:{color};font-weight:700;font-size:0.9rem;\">{escape(label)}</span>"
    )


def _render_dependency_rows(services: dict[str, DependencyStatus]) -> str:
    rows: list[str] = []
    for name, service in services.items():
        backend = f"<div style=\"color:#6b7280;font-size:0.9rem;\">backend: {escape(service.backend)}</div>" if service.backend else ""
        rows.append(
            "<tr>"
            f"<td style=\"padding:0.75rem 1rem;border-bottom:1px solid #e5eaef;font-weight:600;\">{escape(name)}</td>"
            f"<td style=\"padding:0.75rem 1rem;border-bottom:1px solid #e5eaef;\">{_status_badge(service.status)}</td>"
            f"<td style=\"padding:0.75rem 1rem;border-bottom:1px solid #e5eaef;\">{escape(service.detail)}{backend}</td>"
            "</tr>"
        )
    return "".join(rows)


def _render_ollama_models(models: list[OllamaConfiguredModelStatus]) -> str:
    items: list[str] = []
    for model in models:
        name = model.name or "unconfigured"
        roles = ", ".join(model.roles) if model.roles else "none"
        items.append(
            "<tr>"
            f"<td style=\"padding:0.75rem 1rem;border-bottom:1px solid #e5eaef;font-weight:600;\">{escape(name)}</td>"
            f"<td style=\"padding:0.75rem 1rem;border-bottom:1px solid #e5eaef;\">{escape(roles)}</td>"
            f"<td style=\"padding:0.75rem 1rem;border-bottom:1px solid #e5eaef;\">{_status_badge(model.status)}</td>"
            f"<td style=\"padding:0.75rem 1rem;border-bottom:1px solid #e5eaef;\">{escape(model.detail)}</td>"
            "</tr>"
        )
    return "".join(items)


def render_runtime_status_page(payload: RuntimeStatusResponse, *, json_url: str) -> str:
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{escape(payload.application.name)} Runtime Status</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: "Avenir Next", "Segoe UI", sans-serif;
        background: #f4f8fb;
        color: #1d2b36;
      }}
      body {{
        margin: 0;
        background:
          radial-gradient(circle at top left, rgba(70, 136, 156, 0.18), transparent 32%),
          linear-gradient(180deg, #f7fbfd 0%, #eef4f7 100%);
      }}
      main {{
        max-width: 1100px;
        margin: 0 auto;
        padding: 2rem 1.25rem 3rem;
      }}
      .hero, .panel {{
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid #d9e4ea;
        border-radius: 18px;
        box-shadow: 0 12px 30px rgba(29, 43, 54, 0.08);
      }}
      .hero {{
        padding: 1.5rem;
        margin-bottom: 1.25rem;
      }}
      .panel {{
        padding: 1.25rem;
        margin-top: 1rem;
      }}
      h1, h2 {{
        margin: 0 0 0.75rem;
      }}
      p {{
        margin: 0.25rem 0;
        line-height: 1.5;
      }}
      .meta {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 0.85rem;
        margin-top: 1rem;
      }}
      .meta-card {{
        padding: 0.85rem 1rem;
        border-radius: 14px;
        background: #f8fbfd;
        border: 1px solid #e5eaef;
      }}
      table {{
        width: 100%;
        border-collapse: collapse;
      }}
      th {{
        text-align: left;
        padding: 0.75rem 1rem;
        font-size: 0.92rem;
        color: #52616d;
        border-bottom: 1px solid #d9e4ea;
      }}
      .link {{
        color: #185c7a;
        font-weight: 700;
        text-decoration: none;
      }}
    </style>
  </head>
  <body>
    <main>
      <section class="hero">
        <p style="text-transform:uppercase;letter-spacing:0.08em;color:#52616d;font-size:0.8rem;">Public runtime status</p>
        <h1>{escape(payload.application.name)}</h1>
        <p>Overall status: {_status_badge(payload.status)}</p>
        <p><a class="link" href="{escape(json_url)}">View JSON output</a></p>
        <div class="meta">
          <div class="meta-card">
            <strong>Environment</strong>
            <p>{escape(payload.application.environment)}</p>
          </div>
          <div class="meta-card">
            <strong>API Version</strong>
            <p>{escape(payload.application.version)}</p>
          </div>
          <div class="meta-card">
            <strong>Generated</strong>
            <p>{escape(payload.application.generated_at)}</p>
          </div>
        </div>
      </section>
      <section class="panel">
        <h2>Core Dependencies</h2>
        <table>
          <thead>
            <tr><th>Service</th><th>Status</th><th>Detail</th></tr>
          </thead>
          <tbody>{_render_dependency_rows(payload.services)}</tbody>
        </table>
      </section>
      <section class="panel">
        <h2>Supabase Runtime</h2>
        <p>Status: {_status_badge(payload.supabase.status)}</p>
        <p>{escape(payload.supabase.detail)}</p>
      </section>
      <section class="panel">
        <h2>Ollama Runtime</h2>
        <p>Status: {_status_badge(payload.ollama.status)}</p>
        <p>{escape(payload.ollama.detail)}</p>
        <p>Catalog reachable: {escape(str(payload.ollama.catalog_reachable).lower())}</p>
        <table>
          <thead>
            <tr><th>Configured Model</th><th>Roles</th><th>Status</th><th>Detail</th></tr>
          </thead>
          <tbody>{_render_ollama_models(payload.ollama.configured_models)}</tbody>
        </table>
      </section>
    </main>
  </body>
</html>"""


async def build_readiness_payload(settings: Settings | None = None) -> HealthStatusResponse:
    runtime_settings = settings or get_settings()
    database_status = _check_database(runtime_settings)
    services = {
        "database": database_status,
        "storage": _check_storage(runtime_settings),
        "vector": _check_vector(runtime_settings),
        "graph": _check_graph(runtime_settings, database_status),
        "llm": await _check_llm(runtime_settings),
        "queue": _check_queue(runtime_settings, database_status),
    }
    overall_status = "ok" if all(service.status == "healthy" for service in services.values()) else "degraded"
    return HealthStatusResponse(status=overall_status, services=services)


liveness_router = APIRouter()
readiness_router = APIRouter()
status_router = APIRouter()


@liveness_router.get("/health", response_model=LivenessResponse, tags=["health"])
async def health_liveness() -> LivenessResponse:
    return LivenessResponse(status="ok")


@readiness_router.get("/health", response_model=HealthStatusResponse, tags=["health"])
async def health_readiness() -> HealthStatusResponse:
    return await build_readiness_payload()


@status_router.get("/status", tags=["health"])
async def runtime_status(
    request: Request,
    response_type: str | None = Query(default=None, alias="type"),
):
    payload = await build_runtime_status_payload(app_version=request.app.version or APP_VERSION)
    if response_type == "json":
        return JSONResponse(payload.model_dump(mode="json"))

    json_url = str(request.url.include_query_params(type="json"))
    return HTMLResponse(render_runtime_status_page(payload, json_url=json_url))
