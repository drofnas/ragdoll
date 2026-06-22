from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from ragdoll.api.dependencies import CurrentUserDep, DatabaseSessionDep, PaginationDep, SpaceScopeDep
from ragdoll.api.shared_schemas import ProblemResponse
from ragdoll.modules.search.api.schemas import SearchMode, SearchResponse
from ragdoll.modules.search.application.queries import search_documents

router = APIRouter(prefix="/search", tags=["search"])

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    404: {"model": ProblemResponse, "description": "Requested resource was not found."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


@router.get("", response_model=SearchResponse, responses=COMMON_RESPONSES)
def read_search_results(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    pagination: PaginationDep,
    space_scope: SpaceScopeDep,
    q: str = Query(min_length=1),
    mode: SearchMode = Query(default=SearchMode.COMBINED),
    document_id: UUID | None = Query(default=None),
    file_type: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
) -> SearchResponse:
    return search_documents(
        db,
        current_user.subject,
        pagination,
        space_scope=space_scope,
        query_text=q,
        mode=mode,
        document_id=document_id,
        file_type=file_type,
        entity_type=entity_type,
    )
