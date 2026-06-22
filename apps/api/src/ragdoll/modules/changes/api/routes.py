from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from ragdoll.api.dependencies import CurrentUserDep, DatabaseSessionDep, PaginationDep, SpaceScopeDep
from ragdoll.api.shared_schemas import ProblemResponse
from ragdoll.modules.changes.api.schemas import ChangeEventDetail, ChangeEventReadResult, ChangeListResponse
from ragdoll.modules.changes.application.queries import get_change_detail, list_changes, mark_change_read

router = APIRouter(prefix="/changes", tags=["changes"])

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    404: {"model": ProblemResponse, "description": "Requested change was not found."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


@router.get("", response_model=ChangeListResponse, responses=COMMON_RESPONSES)
def read_changes(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    pagination: PaginationDep,
    space_scope: SpaceScopeDep,
) -> ChangeListResponse:
    return list_changes(db, current_user.subject, pagination, space_scope=space_scope)


@router.get("/{change_id}", response_model=ChangeEventDetail, responses=COMMON_RESPONSES)
def read_change_detail(change_id: UUID, current_user: CurrentUserDep, db: DatabaseSessionDep) -> ChangeEventDetail:
    return get_change_detail(db, current_user.subject, change_id)


@router.post("/{change_id}/read", response_model=ChangeEventReadResult, responses=COMMON_RESPONSES)
def read_change(change_id: UUID, current_user: CurrentUserDep, db: DatabaseSessionDep) -> ChangeEventReadResult:
    return mark_change_read(db, current_user.subject, change_id)
