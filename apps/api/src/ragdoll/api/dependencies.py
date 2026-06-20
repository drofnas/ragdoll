from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Depends, Query, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.core.auth import AuthenticatedPrincipal, decode_principal_from_token, get_bearer_token
from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import ApplicationError, AuthenticationRequiredError, AuthorizationError
from ragdoll.core.pagination import PaginationParams, resolve_pagination_params
from ragdoll.modules.users.application.queries import build_authenticated_principal, get_user_by_subject
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


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
RequestIdDep = Annotated[str, Depends(get_request_id)]
PaginationDep = Annotated[PaginationParams, Depends(resolve_pagination_params)]
DatabaseSessionDep = Annotated[Session, Depends(get_db_session)]


def require_current_user(
    token: Annotated[str, Depends(get_bearer_token)],
    db: DatabaseSessionDep,
) -> AuthenticatedPrincipal:
    """Resolve the authenticated user principal from the bearer token."""
    payload = decode_principal_from_token(token)
    subject = str(payload.get("sub") or "").strip()
    if not subject:
        raise AuthenticationRequiredError("Authentication token subject is missing.")
    user = get_user_by_subject(db, subject)
    return build_authenticated_principal(user)


def require_admin_user(current_user: CurrentUserDep) -> AuthenticatedPrincipal:
    """Require an authenticated admin user."""
    if not current_user.is_admin:
        raise AuthorizationError("Admin access is required for this resource.")
    return current_user


def require_space_scope(
    space_id: Annotated[UUID | None, Query()] = None,
    all_spaces: Annotated[bool, Query()] = False,
) -> SpaceScope:
    """Resolve shared Space scope query parameters."""
    try:
        return SpaceScope(space_id=space_id, all_spaces=all_spaces)
    except ValidationError as exc:
        raise ApplicationError(
            "The request payload or parameters did not match the expected schema.",
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        ) from exc


CurrentUserDep = Annotated[AuthenticatedPrincipal, Depends(require_current_user)]
AdminUserDep = Annotated[AuthenticatedPrincipal, Depends(require_admin_user)]
SpaceScopeDep = Annotated[SpaceScope, Depends(require_space_scope)]
