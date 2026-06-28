from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from ragdoll.api.dependencies import CurrentUserDep, DatabaseSessionDep, PaginationDep, SpaceScopeDep
from ragdoll.api.shared_schemas import ProblemResponse
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids
from ragdoll.modules.tracked_state.api.schemas import (
    TrackedFieldCreateRequest,
    TrackedFieldDefinition,
    TrackedFieldDefinitionListResponse,
    TrackedFieldSummary,
    TrackedFieldUpdateRequest,
    TrackedStateConflictResponse,
    TrackedStateSummaryResponse,
)
from ragdoll.modules.tracked_state.application.queries import get_tracked_conflicts, get_tracked_summary, list_tracked_fields
from ragdoll.modules.tracked_state.application.service import (
    build_field_definition,
    create_tracked_field,
    recompute_tracked_field,
    update_tracked_field,
)
from ragdoll.modules.tracked_state.infrastructure.repository import TrackedStateRepository

router = APIRouter(prefix="/tracked-state", tags=["tracked_state"])

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    404: {"model": ProblemResponse, "description": "Requested tracked field was not found."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


@router.get("/fields", response_model=TrackedFieldDefinitionListResponse, responses=COMMON_RESPONSES)
def read_tracked_fields(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    pagination: PaginationDep,
    space_scope: SpaceScopeDep,
) -> TrackedFieldDefinitionListResponse:
    return list_tracked_fields(db, current_user.subject, pagination, space_scope=space_scope)


@router.post("/fields", response_model=TrackedFieldDefinition, responses=COMMON_RESPONSES)
def post_tracked_field(
    payload: TrackedFieldCreateRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> TrackedFieldDefinition:
    field = create_tracked_field(db, current_user.subject, space_scope=space_scope, payload=payload)
    recompute_tracked_field(db, current_user.subject, field)
    return build_field_definition(field)


@router.patch("/fields/{field_id}", response_model=TrackedFieldDefinition, responses=COMMON_RESPONSES)
def patch_tracked_field(
    field_id: UUID,
    payload: TrackedFieldUpdateRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> TrackedFieldDefinition:
    repo = TrackedStateRepository(db)
    field = repo.get_visible_or_404(resolve_owned_space_ids(db, UUID(current_user.subject), space_scope), field_id)
    updated = update_tracked_field(db, field, payload=payload)
    recompute_tracked_field(db, current_user.subject, updated)
    return build_field_definition(updated)


@router.get("/summary", response_model=TrackedStateSummaryResponse, responses=COMMON_RESPONSES)
def read_tracked_summary(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> TrackedStateSummaryResponse:
    return get_tracked_summary(db, current_user.subject, space_scope=space_scope)


@router.get("/conflicts", response_model=TrackedStateConflictResponse, responses=COMMON_RESPONSES)
def read_tracked_conflicts(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> TrackedStateConflictResponse:
    return get_tracked_conflicts(db, current_user.subject, space_scope=space_scope)


@router.post("/fields/{field_id}/recompute", response_model=TrackedFieldSummary, responses=COMMON_RESPONSES)
def post_recompute_tracked_field(
    field_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> TrackedFieldSummary:
    repo = TrackedStateRepository(db)
    field = repo.get_visible_or_404(resolve_owned_space_ids(db, UUID(current_user.subject), space_scope), field_id)
    return recompute_tracked_field(db, current_user.subject, field)
