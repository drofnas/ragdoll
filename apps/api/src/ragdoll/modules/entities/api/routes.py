from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from ragdoll.api.dependencies import CurrentUserDep, DatabaseSessionDep, PaginationDep, SpaceScopeDep
from ragdoll.api.shared_schemas import ProblemResponse
from ragdoll.modules.entities.api.schemas import EntityDetailResponse, EntityListResponse
from ragdoll.modules.entities.application.queries import get_entity_detail, list_entities

router = APIRouter(prefix="/entities", tags=["entities"])

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    404: {"model": ProblemResponse, "description": "Requested entity was not found."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


@router.get("", response_model=EntityListResponse, responses=COMMON_RESPONSES)
def read_entities(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    pagination: PaginationDep,
    space_scope: SpaceScopeDep,
    q: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
) -> EntityListResponse:
    return list_entities(
        db,
        current_user.subject,
        pagination,
        space_scope=space_scope,
        query_text=q,
        entity_type=entity_type,
    )


@router.get("/{entity_id}", response_model=EntityDetailResponse, responses=COMMON_RESPONSES)
def read_entity_detail(
    entity_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> EntityDetailResponse:
    return get_entity_detail(db, current_user.subject, entity_id, space_scope=space_scope)
