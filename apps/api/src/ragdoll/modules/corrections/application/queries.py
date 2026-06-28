from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope, SourceTier
from ragdoll.core.pagination import PaginationParams
from ragdoll.modules.corrections.api.schemas import CorrectionListResponse, CorrectionRecordResponse
from ragdoll.modules.corrections.application.service import correction_citation
from ragdoll.modules.corrections.infrastructure.repository import CorrectionsRepository
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids


def build_correction_response(correction) -> CorrectionRecordResponse:
    tier = SourceTier.VERIFIED if correction.status == "verified" else SourceTier.USER
    return CorrectionRecordResponse(
        id=correction.id,
        space_id=correction.space_id,
        submitted_by=correction.submitted_by,
        chat_session_id=correction.chat_session_id,
        chat_message_id=correction.chat_message_id,
        pinned_fact_id=correction.pinned_fact_id,
        document_id=correction.document_id,
        entity_id=correction.entity_id,
        locator_text=correction.locator_text,
        proposed_value=correction.proposed_value,
        rationale=correction.rationale,
        status=correction.status,
        review_notes=correction.review_notes,
        reviewed_by=correction.reviewed_by,
        reviewed_at=correction.reviewed_at,
        created_at=correction.created_at,
        updated_at=correction.updated_at,
        citation=correction_citation(correction, source_tier=tier),
    )


def list_corrections(
    session: Session,
    subject: str,
    pagination: PaginationParams,
    *,
    space_scope: SpaceScope,
    status: str | None,
) -> CorrectionListResponse:
    repo = CorrectionsRepository(session)
    corrections = repo.list_visible(resolve_owned_space_ids(session, UUID(subject), space_scope), status=status)
    total = len(corrections)
    page_items = corrections[pagination.offset : pagination.offset + pagination.page_size]
    return CorrectionListResponse(
        items=[build_correction_response(correction) for correction in page_items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_correction_detail(session: Session, subject: str, correction_id: UUID) -> CorrectionRecordResponse:
    repo = CorrectionsRepository(session)
    correction = repo.get_visible_or_404(
        resolve_owned_space_ids(session, UUID(subject), SpaceScope(all_spaces=True)),
        correction_id,
    )
    return build_correction_response(correction)
