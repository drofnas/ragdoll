from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from ragdoll.api.dependencies import AdminUserDep, DatabaseSessionDep, PaginationDep, SettingsDep
from ragdoll.api.shared_schemas import ProblemResponse
from ragdoll.modules.admin.api.schemas import (
    AdminEffectiveLimitsResponse,
    AdminManagedUserListResponse,
    AdminManagedUserResponse,
    AdminUpdateUserRequest,
)
from ragdoll.modules.admin.application.commands import update_managed_user
from ragdoll.modules.admin.application.queries import (
    build_admin_user_response,
    get_effective_limits,
    get_managed_user,
    list_managed_users,
)

router = APIRouter(prefix="/admin", tags=["admin"])

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    403: {"model": ProblemResponse, "description": "Admin access required."},
    404: {"model": ProblemResponse, "description": "Requested user was not found."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


@router.get("/users", response_model=AdminManagedUserListResponse, responses=COMMON_RESPONSES)
def read_managed_users(
    current_user: AdminUserDep,
    db: DatabaseSessionDep,
    pagination: PaginationDep,
) -> AdminManagedUserListResponse:
    return list_managed_users(db, pagination)


@router.get("/users/{user_id}", response_model=AdminManagedUserResponse, responses=COMMON_RESPONSES)
def read_managed_user(
    user_id: UUID,
    current_user: AdminUserDep,
    db: DatabaseSessionDep,
) -> AdminManagedUserResponse:
    return get_managed_user(db, user_id)


@router.patch("/users/{user_id}", response_model=AdminManagedUserResponse, responses=COMMON_RESPONSES)
def patch_managed_user(
    user_id: UUID,
    payload: AdminUpdateUserRequest,
    current_user: AdminUserDep,
    db: DatabaseSessionDep,
) -> AdminManagedUserResponse:
    updated_user = update_managed_user(db, user_id, payload)
    return build_admin_user_response(updated_user)


@router.get("/effective-limits", response_model=AdminEffectiveLimitsResponse, responses=COMMON_RESPONSES)
def read_effective_limits(
    current_user: AdminUserDep,
    settings: SettingsDep,
) -> AdminEffectiveLimitsResponse:
    return get_effective_limits(settings)
