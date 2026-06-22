from __future__ import annotations

import time
from uuid import uuid4

import httpx
from sqlalchemy import text

from ragdoll.core.config import get_settings
from ragdoll.platform.db.engine import get_engine
from ragdoll.workers.document_pipeline import drain_document_jobs


BASE_URL = "http://127.0.0.1:8000"


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _request(method: str, path: str, **kwargs) -> httpx.Response:
    response = httpx.request(method, f"{BASE_URL}{path}", timeout=20.0, **kwargs)
    response.raise_for_status()
    return response


def _model_available(discovered: set[str], configured_name: str) -> bool:
    if configured_name in discovered:
        return True
    return any(name == configured_name or name.startswith(f"{configured_name}:") for name in discovered)


def _verify_readiness() -> None:
    deadline = time.monotonic() + 60
    last_services: dict[str, dict[str, str]] | None = None
    while time.monotonic() < deadline:
        payload = _request("GET", "/api/v1/health").json()
        services = payload["services"]
        last_services = services
        if all(services[key]["status"] == "healthy" for key in ("database", "storage", "vector", "graph", "llm")):
            return
        time.sleep(1)

    details = {
        key: (last_services or {}).get(key, {}).get("status", "missing")
        for key in ("database", "storage", "vector", "graph", "llm")
    }
    raise RuntimeError(f"Expected readiness services to become healthy, last observed statuses: {details}")


def _verify_pgvector() -> None:
    with get_engine().connect() as connection:
        row = connection.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).first()
    _assert(row is not None, "Expected pgvector extension to be installed.")


def _verify_storage_bucket(settings) -> None:
    response = httpx.get(
        f"{(settings.supabase_url or '').rstrip('/')}/storage/v1/bucket",
        headers={
            "authorization": f"Bearer {(settings.supabase_service_role_key or '').strip()}",
            "apikey": (settings.supabase_service_role_key or "").strip(),
        },
        timeout=20.0,
    )
    response.raise_for_status()
    buckets = response.json()
    bucket_name = settings.effective_storage_bucket
    found = any(
        ((item.get("name") or item.get("id")) if isinstance(item, dict) else None) == bucket_name
        for item in (buckets or [])
    )
    _assert(found, f"Expected Supabase bucket '{bucket_name}' to exist.")


def _verify_ollama_catalog(settings) -> None:
    deadline = time.monotonic() + 180
    discovered: set[str] = set()
    while time.monotonic() < deadline:
        response = httpx.get(f"{(settings.ollama_base_url or '').rstrip('/')}/api/tags", timeout=20.0)
        response.raise_for_status()
        payload = response.json()
        models = payload.get("models")
        _assert(isinstance(models, list), "Expected Ollama /api/tags to return a model list.")
        discovered = {
            item["name"]
            for item in models
            if isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"].strip()
        }
        if discovered and _model_available(discovered, settings.ollama_model) and _model_available(
            discovered, settings.ollama_embedding_model
        ):
            return
        time.sleep(2)

    raise RuntimeError(
        "Expected configured Ollama models to become available, "
        f"but last observed catalog was: {sorted(discovered)}"
    )


def _register_and_login() -> str:
    email = f"infra-smoke-{uuid4().hex}@example.com"
    password = "phase7smoke123"
    _request(
        "POST",
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Infra Smoke"},
    )
    response = _request(
        "POST",
        "/api/v1/auth/login",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        content=f"username={email}&password={password}",
    )
    payload = response.json()
    token = payload.get("access_token")
    _assert(isinstance(token, str) and token, "Expected login to return an access token.")
    return token


def _exercise_upload_flow(token: str) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    upload = _request(
        "POST",
        "/api/v1/ingestion/uploads",
        headers=headers,
        files={"file": ("phase7-smoke.md", b"# Phase 7\n\nLocal infra smoke verification.\n", "text/markdown")},
    ).json()
    document_id = upload["document_id"]

    processed = drain_document_jobs(max_jobs=5)
    _assert(processed >= 1, "Expected at least one queued ingestion job to be processed.")

    status_payload = _request("GET", f"/api/v1/ingestion/documents/{document_id}/status", headers=headers).json()
    _assert(
        status_payload["processing_status"]["overall"] == "completed",
        "Expected uploaded document processing to complete.",
    )
    _assert(status_payload["chunk_count"] >= 1, "Expected uploaded document to produce chunks.")
    _assert(status_payload["indexed_chunk_count"] >= 1, "Expected uploaded document to index chunks.")

    detail = _request("GET", f"/api/v1/documents/{document_id}", headers=headers).json()
    preview = detail.get("preview_text") or ""
    _assert(preview.startswith("# Phase 7"), "Expected document preview text to reflect uploaded markdown.")

    download = _request("GET", f"/api/v1/documents/{document_id}/download", headers=headers)
    _assert(
        b"Local infra smoke verification." in download.content,
        "Expected downloaded original blob to match the uploaded content.",
    )


def main() -> None:
    settings = get_settings()
    _verify_readiness()
    _verify_pgvector()
    _verify_storage_bucket(settings)
    _verify_ollama_catalog(settings)
    token = _register_and_login()
    _exercise_upload_flow(token)
    print("Phase 7 infra smoke passed.")


if __name__ == "__main__":
    main()
