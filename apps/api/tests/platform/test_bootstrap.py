from fastapi import APIRouter
from fastapi.testclient import TestClient

from ragdoll.core.exceptions import ApplicationError
from ragdoll.main import app, create_app


def test_app_import_exposes_fastapi_instance():
    assert app.title == "Ragdoll API"


def test_liveness_endpoint_returns_ok():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_endpoint_returns_phase_1_scaffold():
    client = TestClient(app)
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"degraded", "ok"}
    assert set(data["services"]) == {"database", "storage", "vector", "graph", "llm", "queue"}
    assert data["services"]["queue"]["status"] in {"not_configured", "healthy", "unhealthy"}


def test_runtime_status_html_is_public_and_human_readable():
    client = TestClient(app)
    response = client.get("/status")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Public runtime status" in response.text
    assert "View JSON output" in response.text


def test_runtime_status_json_is_public():
    client = TestClient(app)
    response = client.get("/status?type=json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    payload = response.json()
    assert payload["application"]["name"] == "Ragdoll API"
    assert set(payload["services"]) == {"database", "storage", "vector", "graph", "llm", "queue"}
    assert "supabase" in payload
    assert "ollama" in payload


def test_runtime_status_falls_back_to_html_for_non_json_type():
    client = TestClient(app)
    response = client.get("/status?type=html")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_application_error_uses_problem_json_contract():
    test_app = create_app()
    router = APIRouter()

    @router.get("/boom")
    async def boom():
        raise ApplicationError(
            "Synthetic application failure.",
            status_code=418,
            title="Synthetic error",
            type_uri="https://ragdoll.dev/problems/synthetic-error",
            code="synthetic_error",
        )

    test_app.include_router(router)
    client = TestClient(test_app)
    response = client.get("/boom")

    assert response.status_code == 418
    assert response.headers["content-type"].startswith("application/problem+json")
    payload = response.json()
    assert payload["type"] == "https://ragdoll.dev/problems/synthetic-error"
    assert payload["title"] == "Synthetic error"
    assert payload["status"] == 418
    assert payload["detail"] == "Synthetic application failure."


def test_app_boots_without_feature_runtime_wiring():
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
