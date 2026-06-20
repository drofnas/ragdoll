from functools import lru_cache
from urllib.parse import quote_plus

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings for the clean-room backend scaffold."""

    app_name: str = "Ragdoll API"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:8030"])
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

    feature_flag_unified_search: bool = True

    upload_rate_limit_enabled: bool = True
    upload_rate_limit_requests: int = 10
    upload_rate_limit_window_seconds: int = 60

    e2e_memory_backends: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

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
