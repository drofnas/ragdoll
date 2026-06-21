from datetime import timedelta

import pytest
from pydantic import ValidationError

from ragdoll.api import health as health_module
from ragdoll.api.health import build_readiness_payload, build_runtime_status_payload
from ragdoll.core import config as config_module
from ragdoll.core.config import Settings
from ragdoll.core.exceptions import AuthenticationRequiredError, ConfigurationError
from ragdoll.core.feature_flags import (
    FLAG_DOCUMENT_VERSION_HISTORY,
    FLAG_SEARCH_GRAPH_MODE,
    FLAG_UNIFIED_SEARCH,
    PlanTier,
    resolve_feature_flags,
)
from ragdoll.core.pagination import PaginationParams
from ragdoll.core.security import create_access_token, decode_access_token, get_password_hash, verify_password
from ragdoll.main import create_app
from ragdoll.platform.db import engine as engine_module


class FakeResult:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class FakeConnection:
    def __init__(self, *, vector_installed: bool = True):
        self.vector_installed = vector_installed

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, statement):
        sql = str(statement)
        if "pg_extension" in sql:
            return FakeResult(("vector",) if self.vector_installed else None)
        return FakeResult((1,))


class FakeEngine:
    def __init__(self, *, vector_installed: bool = True):
        self.vector_installed = vector_installed

    def connect(self):
        return FakeConnection(vector_installed=self.vector_installed)


class FakeResponse:
    def __init__(self, payload, *, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeAsyncClient:
    def __init__(self, payload=None, *, error: Exception | None = None, timeout: float = 5.0):
        self.payload = payload or {"models": []}
        self.error = error
        self.timeout = timeout

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str):
        if self.error is not None:
            raise self.error
        return FakeResponse(self.payload)


def test_settings_prefers_main_supabase_database_url():
    settings = Settings(
        supabase_db_url="postgresql://postgres:secret@db.example:5432/postgres",
        _env_file=None,
    )
    assert settings.effective_database_url == "postgresql://postgres:secret@db.example:5432/postgres"


def test_settings_falls_back_to_legacy_split_database_fields():
    settings = Settings(
        supabase_postgres_host="db.example",
        supabase_postgres_port=5432,
        supabase_postgres_db="postgres",
        supabase_postgres_user="postgres",
        supabase_postgres_password="secret",
        _env_file=None,
    )
    assert settings.legacy_supabase_db_url == "postgresql://postgres:secret@db.example:5432/postgres"


def test_settings_accept_allowed_origins_as_single_string():
    assert config_module._normalize_allowed_origins("http://localhost:8030") == ["http://localhost:8030"]


def test_settings_accept_allowed_origins_as_csv_string():
    assert config_module._normalize_allowed_origins("http://localhost:8030, http://localhost:3000") == [
        "http://localhost:8030",
        "http://localhost:3000",
    ]


def test_settings_accept_allowed_origins_as_json_array_string():
    assert config_module._normalize_allowed_origins(
        '["http://localhost:8030", "http://localhost:3000"]'
    ) == ["http://localhost:8030", "http://localhost:3000"]


def test_settings_accept_allowed_origins_as_direct_list():
    assert config_module._normalize_allowed_origins(
        ["http://localhost:8030", " http://localhost:3000 "]
    ) == ["http://localhost:8030", "http://localhost:3000"]


def test_settings_reject_invalid_allowed_origins_from_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "[1, 2]")
    with pytest.raises(ValidationError, match="ALLOWED_ORIGINS"):
        Settings(_env_file=None)


def test_settings_load_allowed_origins_from_env_csv(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:8030,http://localhost:3000")
    settings = Settings(_env_file=None)
    assert settings.allowed_origins == ["http://localhost:8030", "http://localhost:3000"]


def test_settings_load_allowed_origins_from_env_json(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", '["http://localhost:8030", "http://localhost:3000"]')
    settings = Settings(_env_file=None)
    assert settings.allowed_origins == ["http://localhost:8030", "http://localhost:3000"]


def test_create_app_succeeds_with_single_origin_env(monkeypatch):
    monkeypatch.setenv("ALLOWED_ORIGINS", "http://localhost:8030")
    config_module.get_settings.cache_clear()
    try:
        app = create_app()
        assert app.title == "Ragdoll API"
    finally:
        config_module.get_settings.cache_clear()


def test_password_hash_round_trip():
    hashed = get_password_hash("super-secret")
    assert verify_password("super-secret", hashed) is True
    assert verify_password("wrong-secret", hashed) is False


def test_access_token_round_trip_uses_runtime_settings():
    settings = Settings(secret_key="test-secret", access_token_expire_minutes=5, _env_file=None)
    token = create_access_token({"sub": "user-1"}, expires_delta=timedelta(minutes=5), settings=settings)
    payload = decode_access_token(token, settings=settings)
    assert payload["sub"] == "user-1"


def test_invalid_access_token_raises_authentication_error():
    settings = Settings(secret_key="test-secret", _env_file=None)
    with pytest.raises(AuthenticationRequiredError):
        decode_access_token("invalid-token", settings=settings)


def test_feature_flags_support_overrides_and_global_disable():
    flags = resolve_feature_flags(
        PlanTier.FREE,
        overrides={FLAG_UNIFIED_SEARCH: False},
        global_unified_search_enabled=False,
    )
    assert flags[FLAG_UNIFIED_SEARCH] is False


def test_feature_flags_vary_by_plan_tier():
    free_flags = resolve_feature_flags(PlanTier.FREE, global_unified_search_enabled=True)
    pro_flags = resolve_feature_flags(PlanTier.PRO, global_unified_search_enabled=True)
    internal_flags = resolve_feature_flags(PlanTier.INTERNAL, global_unified_search_enabled=True)

    assert free_flags[FLAG_SEARCH_GRAPH_MODE] is False
    assert pro_flags[FLAG_SEARCH_GRAPH_MODE] is True
    assert pro_flags[FLAG_DOCUMENT_VERSION_HISTORY] is False
    assert internal_flags[FLAG_DOCUMENT_VERSION_HISTORY] is True


def test_pagination_params_offset_calculation():
    params = PaginationParams(page=3, page_size=25)
    assert params.offset == 50


def test_db_engine_module_does_not_create_engine_until_requested():
    assert hasattr(engine_module, "get_engine")


@pytest.mark.asyncio
async def test_readiness_payload_marks_queue_not_configured_by_default():
    payload = await build_readiness_payload(Settings(_env_file=None))
    assert payload.services["queue"].status == "not_configured"


@pytest.mark.asyncio
async def test_readiness_payload_marks_database_healthy_when_probe_succeeds(monkeypatch):
    settings = Settings(database_url="postgresql://postgres:secret@db.example:5432/postgres", _env_file=None)

    monkeypatch.setattr(health_module, "get_engine", lambda: FakeEngine())
    payload = await build_readiness_payload(settings)

    assert payload.services["database"].status == "healthy"


@pytest.mark.asyncio
async def test_readiness_payload_marks_storage_healthy_when_bucket_exists(monkeypatch):
    settings = Settings(
        supabase_url="https://supabase.example",
        supabase_service_role_key="service-role-key",
        supabase_storage_bucket="ragdoll",
        _env_file=None,
    )

    monkeypatch.setattr(
        health_module.httpx,
        "get",
        lambda *args, **kwargs: FakeResponse([{"name": "ragdoll"}]),
    )

    payload = await build_readiness_payload(settings)

    assert payload.services["storage"].status == "healthy"
    assert payload.services["storage"].backend == "supabase"


@pytest.mark.asyncio
async def test_readiness_payload_marks_vector_not_configured_without_pgvector(monkeypatch):
    settings = Settings(database_url="postgresql://postgres:secret@db.example:5432/postgres", _env_file=None)

    monkeypatch.setattr(health_module, "get_engine", lambda: FakeEngine(vector_installed=False))
    payload = await build_readiness_payload(settings)

    assert payload.services["vector"].status == "not_configured"


@pytest.mark.asyncio
async def test_readiness_payload_marks_graph_healthy_in_memory_mode():
    payload = await build_readiness_payload(Settings(e2e_memory_backends=True, _env_file=None))
    assert payload.services["graph"].status == "healthy"
    assert payload.services["graph"].backend == "memory"


@pytest.mark.asyncio
async def test_readiness_payload_marks_llm_unhealthy_when_probe_fails(monkeypatch):
    settings = Settings(ollama_base_url="http://ollama.local:11434", _env_file=None)

    monkeypatch.setattr(
        health_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: FakeAsyncClient(error=RuntimeError("connection refused")),
    )

    payload = await build_readiness_payload(settings)

    assert payload.services["llm"].status == "unhealthy"


@pytest.mark.asyncio
async def test_runtime_status_payload_marks_configured_ollama_models_present(monkeypatch):
    settings = Settings(
        app_name="Ragdoll API",
        app_env="development",
        ollama_base_url="http://ollama.local:11434",
        ollama_model="qwen3.5:0.8b",
        ollama_embedding_model="nomic-embed-text",
        _env_file=None,
    )

    monkeypatch.setattr(health_module, "get_engine", lambda: FakeEngine())
    monkeypatch.setattr(
        health_module.httpx,
        "get",
        lambda *args, **kwargs: FakeResponse([{"name": "documents"}]),
    )
    monkeypatch.setattr(
        health_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: FakeAsyncClient(
            payload={"models": [{"name": "qwen3.5:0.8b"}, {"name": "nomic-embed-text"}]}
        ),
    )

    payload = await build_runtime_status_payload(settings, app_version="0.1.0")

    models = {entry.name: entry for entry in payload.ollama.configured_models if entry.name}
    assert payload.application.version == "0.1.0"
    assert payload.ollama.status == "healthy"
    assert models["qwen3.5:0.8b"].status == "present"
    assert set(models["qwen3.5:0.8b"].roles) == {"primary_chat", "orchestrator", "worker"}
    assert models["nomic-embed-text"].status == "present"
    assert models["nomic-embed-text"].roles == ["embedding"]


@pytest.mark.asyncio
async def test_runtime_status_payload_marks_missing_ollama_models(monkeypatch):
    settings = Settings(
        ollama_base_url="http://ollama.local:11434",
        ollama_model="qwen3.5:0.8b",
        ollama_embedding_model="nomic-embed-text",
        _env_file=None,
    )

    monkeypatch.setattr(
        health_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: FakeAsyncClient(payload={"models": [{"name": "qwen3.5:0.8b"}]}),
    )

    payload = await build_runtime_status_payload(settings)

    models = {entry.name: entry for entry in payload.ollama.configured_models if entry.name}
    assert models["qwen3.5:0.8b"].status == "present"
    assert models["nomic-embed-text"].status == "missing"


@pytest.mark.asyncio
async def test_runtime_status_payload_marks_models_not_configured_without_base_url():
    payload = await build_runtime_status_payload(
        Settings(
            ollama_base_url=None,
            ollama_model="qwen3.5:0.8b",
            ollama_embedding_model="nomic-embed-text",
            _env_file=None,
        )
    )

    assert payload.ollama.status == "not_configured"
    assert {entry.status for entry in payload.ollama.configured_models} == {"not_configured"}


@pytest.mark.asyncio
async def test_runtime_status_payload_rolls_up_supabase_status(monkeypatch):
    settings = Settings(
        database_url="postgresql://postgres:secret@db.example:5432/postgres",
        supabase_url="https://supabase.example",
        supabase_service_role_key="service-role-key",
        supabase_storage_bucket="documents",
        ollama_base_url="http://ollama.local:11434",
        _env_file=None,
    )

    monkeypatch.setattr(health_module, "get_engine", lambda: FakeEngine(vector_installed=False))
    monkeypatch.setattr(
        health_module.httpx,
        "get",
        lambda *args, **kwargs: FakeResponse([{"name": "documents"}]),
    )
    monkeypatch.setattr(
        health_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: FakeAsyncClient(payload={"models": []}),
    )

    payload = await build_runtime_status_payload(settings)

    assert payload.supabase.status == "degraded"
    assert payload.supabase.services["vector"].status == "not_configured"


def test_get_engine_requires_database_configuration(monkeypatch):
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_POSTGRES_HOST", raising=False)
    monkeypatch.delenv("SUPABASE_POSTGRES_PORT", raising=False)
    monkeypatch.delenv("SUPABASE_POSTGRES_DB", raising=False)
    monkeypatch.delenv("SUPABASE_POSTGRES_USER", raising=False)
    monkeypatch.delenv("SUPABASE_POSTGRES_PASSWORD", raising=False)
    monkeypatch.setattr(engine_module, "get_settings", lambda: Settings(_env_file=None))
    engine_module.get_engine.cache_clear()
    try:
        with pytest.raises(ConfigurationError):
            engine_module.get_engine()
    finally:
        engine_module.get_engine.cache_clear()
