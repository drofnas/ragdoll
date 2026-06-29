from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.modules.changes.application.service import record_change_event
from ragdoll.modules.corrections.infrastructure.repository import CorrectionsRepository
from ragdoll.modules.pinned_facts.application.service import apply_verified_correction_to_fact
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids, resolve_single_owned_space
from ragdoll.modules.pinned_facts.infrastructure.repository import PinnedFactsRepository
from ragdoll.platform.db.models import CorrectionRecord


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def create_correction(session: Session, subject: str, *, space_scope: SpaceScope, payload) -> CorrectionRecord:
    owner_user_id = UUID(subject)
    pinned_fact = None
    if payload.pinned_fact_id is not None:
        pinned_fact = PinnedFactsRepository(session).get_visible_or_404(
            resolve_owned_space_ids(session, owner_user_id, SpaceScope(all_spaces=True)),
            payload.pinned_fact_id,
        )
        space_id = pinned_fact.space_id
    else:
        space_id = resolve_single_owned_space(session, owner_user_id, space_scope).id

    correction = CorrectionRecord(
        space_id=space_id,
        submitted_by=owner_user_id,
        chat_session_id=payload.chat_session_id,
        chat_message_id=payload.chat_message_id,
        pinned_fact_id=pinned_fact.id if pinned_fact is not None else payload.pinned_fact_id,
        document_id=payload.document_id,
        entity_id=payload.entity_id,
        locator_text=payload.locator_text.strip() if payload.locator_text else None,
        proposed_value=payload.proposed_value.strip(),
        rationale=payload.rationale.strip() if payload.rationale else None,
        status="pending",
    )
    repo = CorrectionsRepository(session)
    repo.add(correction)
    session.flush()
    record_change_event(
        session,
        space_id=correction.space_id,
        event_type="correction_submitted",
        title="Correction submitted",
        summary=f"Correction submitted for value {correction.proposed_value}.",
        actor_user_id=owner_user_id,
        correction_id=correction.id,
        pinned_fact_id=correction.pinned_fact_id,
        chat_session_id=correction.chat_session_id,
    )
    session.commit()
    session.refresh(correction)
    return correction


def review_correction(
    session: Session,
    subject: str,
    correction: CorrectionRecord,
    *,
    status: str,
    review_notes: str | None,
) -> CorrectionRecord:
    correction.status = status
    correction.review_notes = review_notes.strip() if review_notes else None
    correction.reviewed_by = UUID(subject)
    correction.reviewed_at = utc_now()
    record_change_event(
        session,
        space_id=correction.space_id,
        event_type=f"correction_{status}",
        title=f"Correction {status}",
        summary=f"Correction was {status}.",
        actor_user_id=UUID(subject),
        correction_id=correction.id,
        pinned_fact_id=correction.pinned_fact_id,
        chat_session_id=correction.chat_session_id,
    )
    session.commit()
    session.refresh(correction)
    if correction.pinned_fact_id is not None and status == "verified":
        fact = PinnedFactsRepository(session).get_visible_or_404([correction.space_id], correction.pinned_fact_id)
        apply_verified_correction_to_fact(session, subject, fact, correction)
    return correction
