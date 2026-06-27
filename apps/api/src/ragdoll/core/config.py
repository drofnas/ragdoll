import json
from functools import lru_cache
from typing import Literal
from urllib.parse import quote_plus

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _normalize_allowed_origins(value: object) -> list[str]:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "ALLOWED_ORIGINS must be a comma-separated string or JSON array of strings."
                ) from exc
            if not isinstance(decoded, list):
                raise ValueError("ALLOWED_ORIGINS JSON form must decode to an array of strings.")
            value = decoded
        else:
            value = text.split(",")

    if isinstance(value, (list, tuple)):
        normalized: list[str] = []
        for item in value:
            if not isinstance(item, str):
                raise ValueError("ALLOWED_ORIGINS entries must be strings.")
            trimmed = item.strip()
            if trimmed:
                normalized.append(trimmed)
        return normalized

    raise ValueError("ALLOWED_ORIGINS must be a string, JSON array string, or list of strings.")


class Settings(BaseSettings):
    """Runtime settings for the clean-room backend scaffold."""

    app_name: str = "Ragdoll API"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    sql_echo: bool = False
    allowed_origins_raw: str = Field(
        default="http://localhost:8030",
        validation_alias=AliasChoices("ALLOWED_ORIGINS", "allowed_origins"),
        exclude=True,
    )
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    database_url: str | None = None
    db_pool_mode: str = "queue"
    db_pool_size: int = Field(default=8, ge=1, le=50)
    db_max_overflow: int = Field(default=2, ge=0, le=100)
    db_pool_timeout_seconds: float = Field(default=10.0, ge=1.0, le=120.0)
    db_pool_recycle_seconds: int = Field(default=300, ge=30, le=86400)
    db_connect_timeout_seconds: int = Field(default=5, ge=1, le=120)

    supabase_db_url: str | None = None
    supabase_test_db_url: str | None = None
    supabase_postgres_host: str | None = None
    supabase_postgres_port: int | None = None
    supabase_postgres_db: str | None = None
    supabase_postgres_user: str | None = None
    supabase_postgres_password: str | None = None
    supabase_url: str | None = None
    supabase_anon_key: str | None = None
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str | None = None
    supabase_test_storage_bucket: str | None = None
    ragdoll_use_test_db: bool = False
    ragdoll_use_test_storage_bucket: bool = False

    secret_key: str = "ragdoll-dev-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    ollama_base_url: str | None = None
    ollama_worker_base_url: str | None = None
    ollama_model: str = "llama3.1:8b"
    ollama_orchestrator_model: str | None = None
    ollama_worker_model: str | None = None
    ollama_embedding_model: str = "nomic-embed-text"
    entity_extraction_mode: Literal["auto", "ollama", "deterministic"] = "auto"
    entity_extraction_batch_size: int = Field(default=4, ge=1, le=5)
    entity_extraction_max_parallel_batches: int = Field(default=2, ge=1, le=4)
    ollama_embedding_dimensions: int = Field(default=768, ge=1, le=4096)
    ollama_worker_timeout_seconds: float = Field(default=120.0, ge=5.0, le=600.0)
    ollama_chat_timeout_seconds: float = Field(default=45.0, ge=5.0, le=600.0)
    ollama_status_chat_timeout_seconds: float = Field(default=45.0, ge=5.0, le=600.0)
    ollama_chat_max_tokens: int = Field(default=700, ge=64, le=4096)
    ollama_chat_context_window: int = Field(default=4096, ge=1024, le=32768)
    ollama_chat_think: bool = False

    instance_limit_documents: int | None = None
    instance_limit_max_file_size_bytes: int | None = Field(default=100 * 1024 * 1024, ge=1)
    instance_limit_chunks: int | None = None
    instance_limit_storage_bytes: int | None = None
    instance_limit_tokens_5h: int | None = None
    instance_limit_tokens_week: int | None = None
    instance_limit_retrieval_chunks: int = Field(default=20, ge=1, le=100)
    instance_limit_output_tokens: int = Field(default=2400, ge=1, le=32768)
    instance_limit_per_document_chunks: int = Field(default=2000, ge=1, le=100000)

    upload_rate_limit_enabled: bool = True
    upload_rate_limit_requests: int = 10
    upload_rate_limit_window_seconds: int = 60
    redis_url: str | None = "redis://redis:6379/0"
    document_processing_queue_name: str = "document-processing"
    document_processing_job_timeout_seconds: int = Field(default=2700, ge=30, le=86400)
    document_processing_result_ttl_seconds: int = Field(default=86400, ge=30, le=604800)
    document_processing_failure_ttl_seconds: int = Field(default=604800, ge=30, le=2592000)
    document_processing_timeout_seconds_default: float = Field(default=600.0, ge=30.0, le=86400.0)
    document_processing_timeout_seconds_extraction: float = Field(default=2700.0, ge=30.0, le=86400.0)

    e2e_shared_backends: bool = False
    e2e_memory_backends: bool = False
    e2e_test_user_email: str | None = None
    e2e_test_user_password: str = "testpass123"
    e2e_test_user_full_name: str = "Ragdoll E2E Test User"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("allowed_origins_raw", mode="before")
    @classmethod
    def parse_allowed_origins_raw(cls, value: object) -> str:
        normalized = _normalize_allowed_origins(value)
        return ",".join(normalized)

    @field_validator("entity_extraction_mode", mode="before")
    @classmethod
    def normalize_entity_extraction_mode(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return _normalize_allowed_origins(self.allowed_origins_raw)

    @property
    def legacy_supabase_db_url(self) -> str:
        host = (self.supabase_postgres_host or "").strip()
        port = self.supabase_postgres_port
        database = (self.supabase_postgres_db or "").strip()
        user = (self.supabase_postgres_user or "").strip()
        password = self.supabase_postgres_password

        if not any((host, port, database, user, password)):
            return ""

        if not all((host, port, database, user, password)):
            return ""

        quoted_user = quote_plus(user)
        quoted_password = quote_plus(password)
        return f"postgresql://{quoted_user}:{quoted_password}@{host}:{port}/{database}"

    @property
    def effective_database_url(self) -> str:
        if self.ragdoll_use_test_db and (self.supabase_test_db_url or "").strip():
            return (self.supabase_test_db_url or "").strip()
        if (self.supabase_db_url or "").strip():
            return (self.supabase_db_url or "").strip()
        if self.legacy_supabase_db_url:
            return self.legacy_supabase_db_url
        return (self.database_url or "").strip()

    @property
    def effective_storage_bucket(self) -> str:
        if self.ragdoll_use_test_storage_bucket and (self.supabase_test_storage_bucket or "").strip():
            return (self.supabase_test_storage_bucket or "").strip()
        return (self.supabase_storage_bucket or "").strip()

    @property
    def active_backend_name(self) -> str:
        if self.e2e_shared_backends:
            return "e2e_shared"
        return "memory" if self.e2e_memory_backends else "supabase"

    @property
    def ollama_orchestrator_model_effective(self) -> str:
        return (self.ollama_orchestrator_model or "").strip() or self.ollama_model

    @property
    def ollama_worker_model_effective(self) -> str:
        return (self.ollama_worker_model or "").strip() or self.ollama_model

    @property
    def ollama_worker_base_url_effective(self) -> str:
        return (self.ollama_worker_base_url or "").strip() or (self.ollama_base_url or "").strip()

    @property
    def has_database_config(self) -> bool:
        return bool(self.effective_database_url)

    @property
    def has_storage_config(self) -> bool:
        return bool(
            (self.supabase_url or "").strip()
            and (self.supabase_service_role_key or "").strip()
            and self.effective_storage_bucket
        )

    @property
    def has_ollama_config(self) -> bool:
        return bool((self.ollama_base_url or "").strip())


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
