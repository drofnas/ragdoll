from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from ragdoll.api.dependencies import CurrentUserDep, DatabaseSessionDep, SpaceScopeDep
from ragdoll.api.shared_schemas import ProblemResponse
from ragdoll.modules.knowledge_graph.api.schemas import GraphResponse
from ragdoll.modules.knowledge_graph.application.queries import get_document_graph, get_entity_subgraph

router = APIRouter(prefix="/knowledge-graph", tags=["knowledge_graph"])

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    404: {"model": ProblemResponse, "description": "Requested graph seed was not found."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


@router.get("/entities/{entity_id}/subgraph", response_model=GraphResponse, responses=COMMON_RESPONSES)
def read_entity_subgraph(
    entity_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
    depth: int = Query(default=1, ge=1, le=3),
    limit: int = Query(default=25, ge=1, le=100),
) -> GraphResponse:
    return get_entity_subgraph(
        db,
        current_user.subject,
        entity_id,
        space_scope=space_scope,
        depth=depth,
        limit=limit,
    )


@router.get("/documents/{document_id}", response_model=GraphResponse, responses=COMMON_RESPONSES)
def read_document_graph(
    document_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
    limit: int = Query(default=50, ge=1, le=100),
) -> GraphResponse:
    return get_document_graph(
        db,
        current_user.subject,
        document_id,
        space_scope=space_scope,
        limit=limit,
    )
