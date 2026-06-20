from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool

from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import ConfigurationError


def _engine_kwargs(settings: Settings) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "pool_pre_ping": True,
        "echo": settings.debug,
        "connect_args": {
            "connect_timeout": settings.db_connect_timeout_seconds,
            "application_name": "ragdoll-api",
        },
    }

    if settings.db_pool_mode == "null":
        kwargs["poolclass"] = NullPool
        return kwargs

    kwargs.update(
        {
            "pool_size": settings.db_pool_size,
            "max_overflow": settings.db_max_overflow,
            "pool_timeout": settings.db_pool_timeout_seconds,
            "pool_recycle": settings.db_pool_recycle_seconds,
            "pool_use_lifo": True,
        }
    )
    return kwargs


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    settings = get_settings()
    database_url = settings.effective_database_url
    if not database_url:
        raise ConfigurationError(
            "Database configuration is not set. Configure SUPABASE_DB_URL or database_url before using DB foundations."
        )
    return create_engine(database_url, **_engine_kwargs(settings))
