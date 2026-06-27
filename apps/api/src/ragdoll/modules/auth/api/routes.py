from __future__ import annotations

from fastapi import APIRouter, Request, status

from ragdoll.api.dependencies import (
    CurrentUserDep,
    DatabaseSessionDep,
    DocumentStorageDep,
    GraphCleanupDep,
    SettingsDep,
    VectorCleanupDep,
)
from ragdoll.api.shared_schemas import MutationResult, ProblemResponse
from ragdoll.core.exceptions import ApplicationError, AuthorizationError
from ragdoll.modules.auth.api.schemas import LoginTokenResponse, RegisterRequest
from ragdoll.modules.auth.application.commands import (
    build_registration_response,
    login_user,
    parse_oauth_password_form,
    register_user,
    reset_user_workspace,
)
from ragdoll.modules.auth.application.queries import get_current_user_profile
from ragdoll.modules.users.domain.policies import normalize_email_address
from ragdoll.modules.users.api.schemas import UpdateCurrentUserRequest, UserProfileResponse
from ragdoll.modules.users.application.commands import update_current_user
from ragdoll.modules.users.application.queries import build_user_profile_response, get_user_by_subject

router = APIRouter(prefix="/auth", tags=["auth"])

LOGIN_OPENAPI_EXTRA = {
    "requestBody": {
        "required": True,
        "content": {
            "application/x-www-form-urlencoded": {
                "schema": {
                    "type": "object",
                    "required": ["username", "password"],
                    "properties": {
                        "username": {"type": "string", "format": "email"},
                        "password": {"type": "string"},
                    },
                }
            }
        },
    }
}

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


@router.post(
    "/register",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
    responses={409: {"model": ProblemResponse, "description": "Email already registered."}, **COMMON_RESPONSES},
)
def register(payload: RegisterRequest, db: DatabaseSessionDep) -> UserProfileResponse:
    user = register_user(db, payload)
    return build_registration_response(user)


@router.post(
    "/login",
    response_model=LoginTokenResponse,
    responses=COMMON_RESPONSES,
    openapi_extra=LOGIN_OPENAPI_EXTRA,
)
async def login(request: Request, db: DatabaseSessionDep) -> LoginTokenResponse:
    username, password = parse_oauth_password_form(await request.body())
    return login_user(db, username, password)


@router.get("/me", response_model=UserProfileResponse, responses=COMMON_RESPONSES)
def read_current_user(current_user: CurrentUserDep, db: DatabaseSessionDep) -> UserProfileResponse:
    return get_current_user_profile(db, current_user)


@router.patch(
    "/me",
    response_model=UserProfileResponse,
    responses={409: {"model": ProblemResponse, "description": "Email already registered."}, **COMMON_RESPONSES},
)
def patch_current_user(
    payload: UpdateCurrentUserRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
) -> UserProfileResponse:
    user = get_user_by_subject(db, current_user.subject)
    updated_user = update_current_user(db, user, payload)
    return build_user_profile_response(updated_user)


@router.post(
    "/e2e/reset-workspace",
    response_model=MutationResult,
    include_in_schema=False,
    responses={
        401: {"model": ProblemResponse, "description": "Authentication required."},
        403: {"model": ProblemResponse, "description": "Reserved for the configured E2E test user."},
        404: {"model": ProblemResponse, "description": "Shared E2E reset is not enabled."},
    },
)
def post_e2e_reset_workspace(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    settings: SettingsDep,
    storage: DocumentStorageDep,
    vector_cleanup: VectorCleanupDep,
    graph_cleanup: GraphCleanupDep,
) -> MutationResult:
    configured_email = (settings.e2e_test_user_email or "").strip()
    if not configured_email:
        raise ApplicationError(
            "Shared E2E test user reset is not enabled.",
            status_code=404,
            title="Not found",
            type_uri="https://ragdoll.dev/problems/not-found",
            code="e2e_test_user_reset_not_enabled",
        )

    if normalize_email_address(current_user.email or "") != normalize_email_address(configured_email):
        raise AuthorizationError("This endpoint is reserved for the configured E2E test user.")

    user = get_user_by_subject(db, current_user.subject)
    reset_user_workspace(
        db,
        user,
        storage=storage,
        vector_cleanup=vector_cleanup,
        graph_cleanup=graph_cleanup,
    )
    return MutationResult(message="Shared E2E test user workspace reset.")
