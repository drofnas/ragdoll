from typing import Annotated
from uuid import uuid4

from fastapi import Depends, Request

from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import RuntimeScaffoldNotReadyError


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


def get_pagination_params() -> dict[str, int]:
    """Placeholder pagination dependency until shared pagination primitives land."""
    return {"page": 1, "page_size": 20}


def require_current_user() -> None:
    """Placeholder current-user dependency for future auth wiring."""
    raise RuntimeScaffoldNotReadyError("Current-user dependency is not wired yet.")


def require_admin_user() -> None:
    """Placeholder admin guard dependency for future auth wiring."""
    raise RuntimeScaffoldNotReadyError("Admin guard dependency is not wired yet.")


def require_space_scope() -> None:
    """Placeholder Space-scope dependency for future scope resolution."""
    raise RuntimeScaffoldNotReadyError("Space-scope dependency is not wired yet.")


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
RequestIdDep = Annotated[str, Depends(get_request_id)]
PaginationDep = Annotated[dict[str, int], Depends(get_pagination_params)]
CurrentUserDep = Annotated[None, Depends(require_current_user)]
AdminUserDep = Annotated[None, Depends(require_admin_user)]
SpaceScopeDep = Annotated[None, Depends(require_space_scope)]
