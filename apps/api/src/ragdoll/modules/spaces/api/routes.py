from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query, status

from ragdoll.api.dependencies import CurrentUserDep, DatabaseSessionDep
from ragdoll.api.shared_schemas import ProblemResponse
from ragdoll.modules.spaces.api.schemas import SpaceCreateRequest, SpaceListResponse, SpaceResponse, SpaceUpdateRequest
from ragdoll.modules.spaces.application.commands import archive_space, create_space, update_space
from ragdoll.modules.spaces.application.queries import build_space_response, get_owned_space_or_404, list_spaces

router = APIRouter(prefix="/spaces", tags=["spaces"])

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    404: {"model": ProblemResponse, "description": "Requested space was not found."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


@router.get("", response_model=SpaceListResponse, responses=COMMON_RESPONSES)
def read_spaces(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    include_archived: bool = Query(default=False),
) -> SpaceListResponse:
    return list_spaces(db, UUID(current_user.subject), include_archived=include_archived)


@router.post("", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED, responses=COMMON_RESPONSES)
def post_space(
    payload: SpaceCreateRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
) -> SpaceResponse:
    space = create_space(db, UUID(current_user.subject), payload)
    return build_space_response(space)


@router.get("/{space_id}", response_model=SpaceResponse, responses=COMMON_RESPONSES)
def read_space(space_id: UUID, current_user: CurrentUserDep, db: DatabaseSessionDep) -> SpaceResponse:
    space = get_owned_space_or_404(db, UUID(current_user.subject), space_id)
    return build_space_response(space)


@router.patch("/{space_id}", response_model=SpaceResponse, responses=COMMON_RESPONSES)
def patch_space(
    space_id: UUID,
    payload: SpaceUpdateRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
) -> SpaceResponse:
    space = get_owned_space_or_404(db, UUID(current_user.subject), space_id)
    updated_space = update_space(db, UUID(current_user.subject), space, payload)
    return build_space_response(updated_space)


@router.delete("/{space_id}", response_model=SpaceResponse, responses=COMMON_RESPONSES)
def delete_space(space_id: UUID, current_user: CurrentUserDep, db: DatabaseSessionDep) -> SpaceResponse:
    space = get_owned_space_or_404(db, UUID(current_user.subject), space_id)
    archived_space = archive_space(db, space)
    return build_space_response(archived_space)
