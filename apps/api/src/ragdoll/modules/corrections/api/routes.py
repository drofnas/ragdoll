from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Query

from ragdoll.api.dependencies import CurrentUserDep, DatabaseSessionDep, PaginationDep, SpaceScopeDep
from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.api.shared_schemas import ProblemResponse
from ragdoll.modules.corrections.api.schemas import (
    CorrectionCreateRequest,
    CorrectionListResponse,
    CorrectionRecordResponse,
    CorrectionReviewRequest,
)
from ragdoll.modules.corrections.application.commands import create_correction, review_correction
from ragdoll.modules.corrections.application.queries import get_correction_detail, list_corrections
from ragdoll.modules.corrections.infrastructure.repository import CorrectionsRepository
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids

router = APIRouter(prefix="/corrections", tags=["corrections"])

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    404: {"model": ProblemResponse, "description": "Requested correction was not found."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


@router.get("", response_model=CorrectionListResponse, responses=COMMON_RESPONSES)
def read_corrections(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    pagination: PaginationDep,
    space_scope: SpaceScopeDep,
    status: str | None = Query(default=None),
) -> CorrectionListResponse:
    return list_corrections(db, current_user.subject, pagination, space_scope=space_scope, status=status)


@router.post("", response_model=CorrectionRecordResponse, responses=COMMON_RESPONSES)
def post_correction(
    payload: CorrectionCreateRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> CorrectionRecordResponse:
    correction = create_correction(db, current_user.subject, space_scope=space_scope, payload=payload)
    return get_correction_detail(db, current_user.subject, correction.id)


@router.get("/{correction_id}", response_model=CorrectionRecordResponse, responses=COMMON_RESPONSES)
def read_correction_detail(
    correction_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
) -> CorrectionRecordResponse:
    return get_correction_detail(db, current_user.subject, correction_id)


@router.post("/{correction_id}/verify", response_model=CorrectionRecordResponse, responses=COMMON_RESPONSES)
def verify_correction(
    correction_id: UUID,
    payload: CorrectionReviewRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
) -> CorrectionRecordResponse:
    repo = CorrectionsRepository(db)
    correction = repo.get_visible_or_404(
        resolve_owned_space_ids(db, UUID(current_user.subject), SpaceScope(all_spaces=True)),
        correction_id,
    )
    review_correction(db, current_user.subject, correction, status="verified", review_notes=payload.review_notes)
    return get_correction_detail(db, current_user.subject, correction_id)


@router.post("/{correction_id}/reject", response_model=CorrectionRecordResponse, responses=COMMON_RESPONSES)
def reject_correction(
    correction_id: UUID,
    payload: CorrectionReviewRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
) -> CorrectionRecordResponse:
    repo = CorrectionsRepository(db)
    correction = repo.get_visible_or_404(
        resolve_owned_space_ids(db, UUID(current_user.subject), SpaceScope(all_spaces=True)),
        correction_id,
    )
    review_correction(db, current_user.subject, correction, status="rejected", review_notes=payload.review_notes)
    return get_correction_detail(db, current_user.subject, correction_id)
