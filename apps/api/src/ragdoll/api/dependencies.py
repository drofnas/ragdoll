from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.core.auth import AuthenticatedPrincipal
from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import RuntimeScaffoldNotReadyError
from ragdoll.core.pagination import PaginationParams, resolve_pagination_params
from ragdoll.platform.db.session import get_db_session


def get_app_settings() -> Settings:
    """Return parsed application settings."""
    return get_settings()


def get_request_id(request: Request) -> str:
    """Return a stable request id for the lifetime of the request."""
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        header_value = request.headers.get("x-request-id")
        request_id = header_value.strip() if header_value else str(uuid4())
        request.state.request_id = request_id
    return request_id


def require_current_user() -> AuthenticatedPrincipal:
    """Placeholder current-user dependency for future auth wiring."""
    raise RuntimeScaffoldNotReadyError("Current-user dependency is not wired yet.")


def require_admin_user() -> AuthenticatedPrincipal:
    """Placeholder admin guard dependency for future auth wiring."""
    raise RuntimeScaffoldNotReadyError("Admin guard dependency is not wired yet.")


def require_space_scope() -> SpaceScope:
    """Placeholder Space-scope dependency for future scope resolution."""
    raise RuntimeScaffoldNotReadyError("Space-scope dependency is not wired yet.")


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
RequestIdDep = Annotated[str, Depends(get_request_id)]
PaginationDep = Annotated[PaginationParams, Depends(resolve_pagination_params)]
DatabaseSessionDep = Annotated[Session, Depends(get_db_session)]
CurrentUserDep = Annotated[AuthenticatedPrincipal, Depends(require_current_user)]
AdminUserDep = Annotated[AuthenticatedPrincipal, Depends(require_admin_user)]
SpaceScopeDep = Annotated[SpaceScope, Depends(require_space_scope)]
