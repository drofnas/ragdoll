from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Query

from ragdoll.api.dependencies import CurrentUserDep, DatabaseSessionDep, PaginationDep, SpaceScopeDep
from ragdoll.api.shared_schemas import ProblemResponse
from ragdoll.modules.pinned_facts.api.schemas import (
    AcceptPinnedFactCandidateRequest,
    PinnedFactCandidate as PinnedFactCandidateResponse,
    PinnedFactCandidateListResponse,
    PinnedFactCreateRequest,
    PinnedFactDetail,
    PinnedFactHistoryResponse,
    PinnedFactListResponse,
    PinnedFactSortKey,
    PinnedFactUpdateRequest,
    RejectPinnedFactCandidateRequest,
)
from ragdoll.modules.pinned_facts.application.queries import (
    get_pinned_fact_detail,
    list_pinned_fact_candidates,
    list_pinned_fact_history,
    list_pinned_facts,
)
from ragdoll.modules.pinned_facts.application.service import (
    accept_pinned_fact_candidate,
    build_candidate,
    build_fact_detail,
    build_value_snapshot,
    create_pinned_fact,
    recheck_pinned_fact,
    reject_pinned_fact_candidate,
    revert_pinned_fact_to_history,
    update_pinned_fact,
)
from ragdoll.modules.pinned_facts.infrastructure.repository import PinnedFactsRepository
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids

router = APIRouter(prefix="/pinned-facts", tags=["pinned_facts"])

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    404: {"model": ProblemResponse, "description": "Requested pinned fact resource was not found."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


@router.get("", response_model=PinnedFactListResponse, responses=COMMON_RESPONSES)
def read_pinned_facts(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    pagination: PaginationDep,
    space_scope: SpaceScopeDep,
    name: str | None = Query(default=None),
    status: str | None = Query(default=None),
    created_by: str | None = Query(default=None),
    updated_by: str | None = Query(default=None),
    created_date: date | None = Query(default=None),
    updated_date: date | None = Query(default=None),
    sort_key: PinnedFactSortKey = Query(default="name"),
    descending: bool = Query(default=False),
) -> PinnedFactListResponse:
    return list_pinned_facts(
        db,
        current_user.subject,
        pagination,
        space_scope=space_scope,
        name=name,
        status=status,
        created_by=created_by,
        updated_by=updated_by,
        created_date=created_date,
        updated_date=updated_date,
        sort_key=sort_key,
        descending=descending,
    )


@router.post("", response_model=PinnedFactDetail, responses=COMMON_RESPONSES)
def post_pinned_fact(
    payload: PinnedFactCreateRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> PinnedFactDetail:
    fact = create_pinned_fact(db, current_user.subject, space_scope=space_scope, payload=payload)
    return build_fact_detail(db, fact)


@router.get("/{fact_id}", response_model=PinnedFactDetail, responses=COMMON_RESPONSES)
def read_pinned_fact_detail(
    fact_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> PinnedFactDetail:
    return get_pinned_fact_detail(db, current_user.subject, fact_id, space_scope=space_scope)


@router.patch("/{fact_id}", response_model=PinnedFactDetail, responses=COMMON_RESPONSES)
def patch_pinned_fact(
    fact_id: UUID,
    payload: PinnedFactUpdateRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> PinnedFactDetail:
    repo = PinnedFactsRepository(db)
    fact = repo.get_visible_or_404(resolve_owned_space_ids(db, UUID(current_user.subject), space_scope), fact_id)
    updated = update_pinned_fact(db, current_user.subject, fact, payload=payload)
    return build_fact_detail(db, updated)


@router.get("/{fact_id}/candidates", response_model=PinnedFactCandidateListResponse, responses=COMMON_RESPONSES)
def read_pinned_fact_candidates(
    fact_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> PinnedFactCandidateListResponse:
    return list_pinned_fact_candidates(db, current_user.subject, fact_id, space_scope=space_scope)


@router.get("/candidates/{candidate_id}", response_model=PinnedFactCandidateResponse, responses=COMMON_RESPONSES)
def read_pinned_fact_candidate_detail(
    candidate_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> PinnedFactCandidateResponse:
    candidate = PinnedFactsRepository(db).get_candidate_visible_or_404(
        resolve_owned_space_ids(db, UUID(current_user.subject), space_scope),
        candidate_id,
    )
    return build_candidate(candidate)


@router.post("/candidates/{candidate_id}/accept", response_model=PinnedFactDetail, responses=COMMON_RESPONSES)
def post_accept_pinned_fact_candidate(
    candidate_id: UUID,
    payload: AcceptPinnedFactCandidateRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> PinnedFactDetail:
    repo = PinnedFactsRepository(db)
    candidate = repo.get_candidate_visible_or_404(resolve_owned_space_ids(db, UUID(current_user.subject), space_scope), candidate_id)
    override_value = None
    if payload.value_kind is not None:
        override_value = build_value_snapshot(kind=payload.value_kind, text=payload.value_text, json_value=payload.value_json)
    fact = accept_pinned_fact_candidate(
        db,
        current_user.subject,
        candidate,
        override_value=override_value,
        review_notes=payload.review_notes,
    )
    return build_fact_detail(db, fact)


@router.post("/candidates/{candidate_id}/reject", response_model=PinnedFactCandidateResponse, responses=COMMON_RESPONSES)
def post_reject_pinned_fact_candidate(
    candidate_id: UUID,
    payload: RejectPinnedFactCandidateRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> PinnedFactCandidateResponse:
    repo = PinnedFactsRepository(db)
    candidate = repo.get_candidate_visible_or_404(resolve_owned_space_ids(db, UUID(current_user.subject), space_scope), candidate_id)
    return build_candidate(reject_pinned_fact_candidate(db, current_user.subject, candidate, review_notes=payload.review_notes))


@router.get("/{fact_id}/history", response_model=PinnedFactHistoryResponse, responses=COMMON_RESPONSES)
def read_pinned_fact_history(
    fact_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> PinnedFactHistoryResponse:
    return list_pinned_fact_history(db, current_user.subject, fact_id, space_scope=space_scope)


@router.post("/{fact_id}/history/{history_id}/revert", response_model=PinnedFactDetail, responses=COMMON_RESPONSES)
def post_revert_pinned_fact_history(
    fact_id: UUID,
    history_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> PinnedFactDetail:
    repo = PinnedFactsRepository(db)
    space_ids = resolve_owned_space_ids(db, UUID(current_user.subject), space_scope)
    fact = repo.get_visible_or_404(space_ids, fact_id)
    history = repo.get_history_visible_or_404(space_ids, history_id)
    reverted = revert_pinned_fact_to_history(db, current_user.subject, fact, history)
    return build_fact_detail(db, reverted)


@router.post("/{fact_id}/recheck", response_model=PinnedFactDetail, responses=COMMON_RESPONSES)
def post_recheck_pinned_fact(
    fact_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> PinnedFactDetail:
    repo = PinnedFactsRepository(db)
    fact = repo.get_visible_or_404(resolve_owned_space_ids(db, UUID(current_user.subject), space_scope), fact_id)
    return recheck_pinned_fact(db, current_user.subject, fact)
