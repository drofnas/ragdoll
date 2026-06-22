from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import Citation, SourceTier, SpaceScope
from ragdoll.modules.changes.application.service import record_change_event
from ragdoll.modules.search.api.schemas import SearchMode, SearchResult
from ragdoll.modules.search.application.evidence import retrieve_search_results
from ragdoll.modules.spaces.application.scope import resolve_single_owned_space
from ragdoll.modules.tracked_state.infrastructure.repository import TrackedStateRepository
from ragdoll.platform.db.models import CorrectionRecord, TrackedField, TrackedFieldValue


@dataclass
class Candidate:
    value_text: str
    source_tier: SourceTier
    status: str
    citations: list[Citation]
    correction_id: UUID | None = None
    created_at: datetime | None = None


def normalize_candidate_value(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _correction_citation(correction: CorrectionRecord, *, source_tier: SourceTier) -> Citation:
    return Citation(
        document_id=correction.document_id,
        entity_id=correction.entity_id,
        locator=correction.locator_text,
        source_tier=source_tier,
    )


def _candidate_from_search_result(result: SearchResult) -> Candidate | None:
    if result.entity is not None:
        value_text = result.entity.display_name.strip()
        source_tier = SourceTier.DERIVED
    else:
        value_text = result.preview_text.strip()
        source_tier = SourceTier.DOCUMENT
    if not value_text:
        return None
    return Candidate(
        value_text=value_text[:500],
        source_tier=source_tier,
        status="retrieved",
        citations=result.citations,
    )


def build_field_definition(field: TrackedField):
    from ragdoll.modules.tracked_state.api.schemas import TrackedFieldDefinition

    return TrackedFieldDefinition(
        id=field.id,
        space_id=field.space_id,
        key=field.key,
        label=field.label,
        prompt=field.prompt,
        entity_type_hint=field.entity_type_hint,
        is_active=field.is_active,
        created_at=field.created_at,
        updated_at=field.updated_at,
    )


def build_value_candidate(candidate: Candidate):
    from ragdoll.modules.tracked_state.api.schemas import TrackedValueCandidate

    return TrackedValueCandidate(
        value_text=candidate.value_text,
        source_tier=candidate.source_tier,
        correction_id=candidate.correction_id,
        citations=candidate.citations,
        created_at=candidate.created_at,
        status=candidate.status,
    )


def _dedupe_candidates(candidates: list[Candidate]) -> list[Candidate]:
    unique: dict[str, Candidate] = {}
    for candidate in candidates:
        key = normalize_candidate_value(candidate.value_text)
        unique.setdefault(key, candidate)
    return list(unique.values())


def _gather_candidates(session: Session, subject: str, field: TrackedField) -> tuple[list[Candidate], list[Candidate], list[Candidate]]:
    repo = TrackedStateRepository(session)
    corrections = repo.list_corrections(field.id)
    verified = [
        Candidate(
            value_text=correction.proposed_value,
            source_tier=SourceTier.VERIFIED,
            status=correction.status,
            citations=[_correction_citation(correction, source_tier=SourceTier.VERIFIED)],
            correction_id=correction.id,
            created_at=correction.reviewed_at or correction.created_at,
        )
        for correction in corrections
        if correction.status == "verified"
    ]
    pending = [
        Candidate(
            value_text=correction.proposed_value,
            source_tier=SourceTier.USER,
            status=correction.status,
            citations=[_correction_citation(correction, source_tier=SourceTier.USER)],
            correction_id=correction.id,
            created_at=correction.created_at,
        )
        for correction in corrections
        if correction.status == "pending"
    ]
    retrieved = [
        candidate
        for candidate in (
            _candidate_from_search_result(result)
            for result in retrieve_search_results(
                session,
                subject,
                space_scope=SpaceScope(space_id=field.space_id),
                query_text=field.prompt,
                mode=SearchMode.COMBINED,
                entity_type=field.entity_type_hint,
                limit=5,
            )
        )
        if candidate is not None
    ]
    return _dedupe_candidates(verified), _dedupe_candidates(pending), _dedupe_candidates(retrieved)


def build_field_summary(session: Session, subject: str, field: TrackedField):
    from ragdoll.modules.tracked_state.api.schemas import TrackedFieldSummary

    verified, pending, retrieved = _gather_candidates(session, subject, field)
    current = TrackedStateRepository(session).get_current_value(field.id)
    status = "empty"
    if len(verified) > 1 or (not verified and len(retrieved) > 1):
        status = "conflict"
    elif pending and current is None and not verified and not retrieved:
        status = "conflict"
    elif verified or retrieved or current is not None:
        status = "resolved"

    return TrackedFieldSummary(
        **build_field_definition(field).model_dump(),
        status=status,
        current_value=current.value_text if current is not None else None,
        current_source_tier=SourceTier(current.source_tier) if current is not None else None,
        current_value_updated_at=current.created_at if current is not None else None,
        conflict_count=(len(verified) if len(verified) > 1 else len(retrieved) if len(retrieved) > 1 else 0),
        pending_correction_count=len(pending),
    )


def build_field_conflict(session: Session, subject: str, field: TrackedField):
    from ragdoll.modules.tracked_state.api.schemas import TrackedStateConflict

    verified, pending, retrieved = _gather_candidates(session, subject, field)
    candidates = verified or retrieved or pending
    status = "empty"
    if len(candidates) > 1 or pending:
        status = "conflict"
    elif candidates:
        status = "resolved"
    return TrackedStateConflict(
        field=build_field_definition(field),
        status=status,
        candidates=[build_value_candidate(candidate) for candidate in [*verified, *pending, *retrieved]],
    )


def recompute_tracked_field(session: Session, subject: str, field: TrackedField):
    repo = TrackedStateRepository(session)
    verified, pending, retrieved = _gather_candidates(session, subject, field)
    winner: Candidate | None = None
    status = "empty"

    if len(verified) == 1:
        winner = verified[0]
        status = "resolved"
    elif len(verified) > 1:
        status = "conflict"
    elif len(retrieved) == 1:
        winner = retrieved[0]
        status = "resolved"
    elif len(retrieved) > 1:
        status = "conflict"
    elif pending:
        status = "conflict"

    current = repo.get_current_value(field.id)
    changed = False
    if winner is not None:
        if (
            current is None
            or current.value_text != winner.value_text
            or current.source_tier != winner.source_tier.value
            or current.resolved_from_correction_id != winner.correction_id
        ):
            repo.clear_current_value(field.id)
            repo.add_value(
                TrackedFieldValue(
                    tracked_field_id=field.id,
                    space_id=field.space_id,
                    resolved_from_correction_id=winner.correction_id,
                    source_tier=winner.source_tier.value,
                    value_text=winner.value_text,
                    citations=[citation.model_dump(mode="json") for citation in winner.citations],
                    is_current=True,
                )
            )
            changed = True
            record_change_event(
                session,
                space_id=field.space_id,
                event_type="tracked_value_updated",
                title=f"Tracked field updated: {field.label}",
                summary=f"{field.label} resolved to {winner.value_text}.",
                actor_user_id=UUID(subject),
                tracked_field_id=field.id,
                payload={"value_text": winner.value_text, "source_tier": winner.source_tier.value},
            )
    else:
        if current is not None:
            repo.clear_current_value(field.id)
            changed = True
        if status == "conflict":
            record_change_event(
                session,
                space_id=field.space_id,
                event_type="tracked_conflict_detected",
                title=f"Tracked field conflict: {field.label}",
                summary=f"Multiple candidate values were found for {field.label}.",
                actor_user_id=UUID(subject),
                tracked_field_id=field.id,
                payload={"candidate_count": len(verified) + len(pending) + len(retrieved)},
            )
    if changed:
        session.flush()
    session.commit()
    session.refresh(field)
    return build_field_summary(session, subject, field)


def create_tracked_field(session: Session, subject: str, *, space_scope: SpaceScope, payload) -> TrackedField:
    owner_user_id = UUID(subject)
    space = resolve_single_owned_space(session, owner_user_id, space_scope)
    field = TrackedField(
        space_id=space.id,
        owner_user_id=owner_user_id,
        key=payload.key.strip(),
        label=payload.label.strip(),
        prompt=payload.prompt.strip(),
        entity_type_hint=payload.entity_type_hint.strip() if payload.entity_type_hint else None,
        is_active=payload.is_active,
    )
    repo = TrackedStateRepository(session)
    repo.add_field(field)
    session.commit()
    session.refresh(field)
    return field


def update_tracked_field(session: Session, field: TrackedField, *, payload) -> TrackedField:
    if payload.label is not None:
        field.label = payload.label.strip()
    if payload.prompt is not None:
        field.prompt = payload.prompt.strip()
    if payload.entity_type_hint is not None:
        field.entity_type_hint = payload.entity_type_hint.strip() or None
    if payload.is_active is not None:
        field.is_active = payload.is_active
    session.commit()
    session.refresh(field)
    return field


def recompute_space_fields(session: Session, subject: str, *, space_id: UUID) -> None:
    repo = TrackedStateRepository(session)
    for field in repo.list_active_fields_for_space(space_id):
        recompute_tracked_field(session, subject, field)
