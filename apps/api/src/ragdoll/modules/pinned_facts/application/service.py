from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import Citation, SourceTier, SpaceScope
from ragdoll.modules.changes.application.service import record_change_event
from ragdoll.modules.corrections.application.service import correction_citation
from ragdoll.modules.pinned_facts.api.schemas import (
    PinnedFactActor,
    PinnedFactCandidate as PinnedFactCandidateSchema,
    PinnedFactDetail,
    PinnedFactEvidence,
    PinnedFactHistoryEntry,
    PinnedFactSummary,
)
from ragdoll.modules.pinned_facts.infrastructure.repository import PinnedFactsRepository
from ragdoll.modules.search.api.schemas import SearchMode, SearchResult
from ragdoll.modules.search.application.evidence import retrieve_search_results
from ragdoll.modules.spaces.application.scope import resolve_single_owned_space
from ragdoll.platform.db.models import PinnedFact, PinnedFactCandidate, PinnedFactHistory, User
from ragdoll.platform.db.models import CorrectionRecord


@dataclass(frozen=True)
class ValueSnapshot:
    kind: str
    text: str | None
    json_value: dict[str, Any] | None


@dataclass(frozen=True)
class DetectedCandidate:
    value: ValueSnapshot
    change_type: str
    confidence: float
    evidence: list[PinnedFactEvidence]
    source_document_id: UUID | None
    idempotency_key: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _value_signature(snapshot: ValueSnapshot) -> str:
    if snapshot.kind == "json":
        return json.dumps(snapshot.json_value or {}, sort_keys=True, separators=(",", ":"))
    return _normalize_whitespace(snapshot.text or "").lower()


def _fact_snapshot(fact: PinnedFact) -> ValueSnapshot | None:
    if fact.value_kind is None:
        return None
    return ValueSnapshot(kind=fact.value_kind, text=fact.value_text, json_value=fact.value_json)


def _evidence_from_raw(raw_items: list[dict[str, Any]] | None) -> list[PinnedFactEvidence]:
    items: list[PinnedFactEvidence] = []
    for raw in raw_items or []:
        try:
            items.append(PinnedFactEvidence.model_validate(raw))
        except ValueError:
            continue
    return items


def _raw_evidence(items: list[PinnedFactEvidence]) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in items]


def _citation_signature(citation: Citation) -> tuple[object, ...]:
    return (
        citation.document_id,
        citation.entity_id,
        citation.chunk_id,
        citation.locator,
        citation.line_number,
        citation.source_tier,
        citation.title,
    )


def _dedupe_evidence(items: list[PinnedFactEvidence]) -> list[PinnedFactEvidence]:
    unique: dict[str, PinnedFactEvidence] = {}
    for item in items:
        citations = sorted(item.citations, key=_citation_signature)
        normalized = PinnedFactEvidence(
            quote=_normalize_whitespace(item.quote),
            citations=citations,
            source_chunk_ids=sorted(set(item.source_chunk_ids)),
        )
        signature = json.dumps(normalized.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        unique.setdefault(signature, normalized)
    return list(unique.values())


def _evidence_signature(items: list[PinnedFactEvidence]) -> str:
    normalized = [item.model_dump(mode="json") for item in _dedupe_evidence(items)]
    normalized.sort(key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    return json.dumps(normalized, sort_keys=True, separators=(",", ":"))


def _citation_document_id(result: SearchResult) -> UUID | None:
    if result.document is not None:
        return result.document.id
    for citation in result.citations:
        if citation.document_id is not None:
            return citation.document_id
    return None


def _evidence_from_search_result(result: SearchResult) -> list[PinnedFactEvidence]:
    quote = _normalize_whitespace(result.preview_text or (result.entity.display_name if result.entity else ""))
    if not quote:
        return []
    return [
        PinnedFactEvidence(
            quote=quote,
            citations=result.citations,
            source_chunk_ids=[citation.chunk_id for citation in result.citations if citation.chunk_id],
        )
    ]


def _detected_from_result(result: SearchResult) -> DetectedCandidate | None:
    value_text = (result.entity.display_name if result.entity is not None else result.preview_text).strip()
    if not value_text:
        return None
    evidence = _evidence_from_search_result(result)
    if not evidence:
        return None
    snapshot = ValueSnapshot(kind="text", text=value_text[:500], json_value=None)
    confidence = 0.93 if result.entity is not None else 0.9
    source_document_id = _citation_document_id(result)
    return DetectedCandidate(
        value=snapshot,
        change_type="update",
        confidence=confidence,
        evidence=evidence,
        source_document_id=source_document_id,
        idempotency_key=f"{source_document_id}:{_value_signature(snapshot)}:{_evidence_signature(evidence)}",
    )


def _actor_for_user_id(session: Session, user_id: UUID | None) -> PinnedFactActor | None:
    if user_id is None:
        return None
    user = session.get(User, user_id)
    if user is None:
        return None
    return PinnedFactActor(id=user.id, email=user.email, full_name=user.full_name)


def _build_summary(session: Session, fact: PinnedFact) -> PinnedFactSummary:
    candidates = PinnedFactsRepository(session).list_candidates_for_fact(fact.id)
    pending_count = sum(1 for candidate in candidates if candidate.status == "pending")
    conflict_count = sum(1 for candidate in candidates if candidate.change_type == "conflict" and candidate.status == "pending")
    history_items = PinnedFactsRepository(session).list_history_for_fact(fact.id)
    latest_history = history_items[0] if history_items else None
    return PinnedFactSummary(
        id=fact.id,
        space_id=fact.space_id,
        key=fact.key,
        title=fact.title,
        description=fact.description,
        entity_type_hint=fact.entity_type_hint,
        is_active=fact.is_active,
        status=fact.status,
        confidence=fact.confidence,
        value_kind=fact.value_kind,
        value_text=fact.value_text,
        value_json=fact.value_json,
        source_document_id=fact.source_document_id,
        evidence=_evidence_from_raw(fact.evidence),
        last_checked_at=fact.last_checked_at,
        pending_candidate_count=pending_count,
        conflict_count=conflict_count,
        created_by=_actor_for_user_id(session, fact.owner_user_id),
        updated_by=_actor_for_user_id(session, latest_history.actor_user_id if latest_history is not None else fact.owner_user_id),
        created_at=fact.created_at,
        updated_at=fact.updated_at,
    )


def build_fact_summary(session: Session, fact: PinnedFact) -> PinnedFactSummary:
    return _build_summary(session, fact)


def build_fact_detail(session: Session, fact: PinnedFact) -> PinnedFactDetail:
    summary = _build_summary(session, fact)
    history_count = len(PinnedFactsRepository(session).list_history_for_fact(fact.id))
    return PinnedFactDetail(**summary.model_dump(), history_count=history_count)


def build_candidate(candidate: PinnedFactCandidate) -> PinnedFactCandidateSchema:
    return PinnedFactCandidateSchema(
        id=candidate.id,
        pinned_fact_id=candidate.pinned_fact_id,
        space_id=candidate.space_id,
        source_document_id=candidate.source_document_id,
        proposed_value_kind=candidate.proposed_value_kind,
        proposed_value_text=candidate.proposed_value_text,
        proposed_value_json=candidate.proposed_value_json,
        change_type=candidate.change_type,
        confidence=candidate.confidence,
        evidence=_evidence_from_raw(candidate.evidence),
        status=candidate.status,
        review_notes=candidate.review_notes,
        reviewed_by=candidate.reviewed_by,
        reviewed_at=candidate.reviewed_at,
        created_at=candidate.created_at,
    )


def build_history_entry(history: PinnedFactHistory) -> PinnedFactHistoryEntry:
    return PinnedFactHistoryEntry(
        id=history.id,
        pinned_fact_id=history.pinned_fact_id,
        candidate_id=history.candidate_id,
        restored_from_history_id=history.restored_from_history_id,
        actor_user_id=history.actor_user_id,
        actor_type=history.actor_type,
        reason=history.reason,
        old_value_kind=history.old_value_kind,
        old_value_text=history.old_value_text,
        old_value_json=history.old_value_json,
        new_value_kind=history.new_value_kind,
        new_value_text=history.new_value_text,
        new_value_json=history.new_value_json,
        old_evidence=_evidence_from_raw(history.old_evidence),
        new_evidence=_evidence_from_raw(history.new_evidence),
        update_note=history.update_note,
        created_at=history.created_at,
    )


def _write_history(
    session: Session,
    *,
    fact: PinnedFact,
    actor_user_id: UUID | None,
    actor_type: str,
    reason: str,
    candidate_id: UUID | None,
    restored_from_history_id: UUID | None,
    old_snapshot: ValueSnapshot | None,
    old_evidence: list[PinnedFactEvidence],
    new_snapshot: ValueSnapshot,
    new_evidence: list[PinnedFactEvidence],
    update_note: str | None,
) -> None:
    PinnedFactsRepository(session).add_history(
        PinnedFactHistory(
            pinned_fact_id=fact.id,
            space_id=fact.space_id,
            candidate_id=candidate_id,
            restored_from_history_id=restored_from_history_id,
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            reason=reason,
            old_value_kind=old_snapshot.kind if old_snapshot is not None else None,
            old_value_text=old_snapshot.text if old_snapshot is not None else None,
            old_value_json=old_snapshot.json_value if old_snapshot is not None else None,
            new_value_kind=new_snapshot.kind,
            new_value_text=new_snapshot.text,
            new_value_json=new_snapshot.json_value,
            old_evidence=_raw_evidence(old_evidence),
            new_evidence=_raw_evidence(new_evidence),
            update_note=update_note.strip() if update_note else None,
        )
    )


def _apply_fact_value(
    session: Session,
    *,
    fact: PinnedFact,
    value: ValueSnapshot,
    confidence: float | None,
    source_document_id: UUID | None,
    evidence: list[PinnedFactEvidence],
    status: str,
    actor_user_id: UUID | None,
    actor_type: str,
    reason: str,
    candidate_id: UUID | None = None,
    restored_from_history_id: UUID | None = None,
    update_note: str | None = None,
) -> None:
    old_snapshot = _fact_snapshot(fact)
    old_evidence = _dedupe_evidence(_evidence_from_raw(fact.evidence))
    fact.value_kind = value.kind
    fact.value_text = value.text
    fact.value_json = value.json_value
    fact.confidence = confidence
    fact.source_document_id = source_document_id
    fact.evidence = _raw_evidence(_dedupe_evidence(evidence))
    fact.status = status
    fact.last_checked_at = utc_now()
    _write_history(
        session,
        fact=fact,
        actor_user_id=actor_user_id,
        actor_type=actor_type,
        reason=reason,
        candidate_id=candidate_id,
        restored_from_history_id=restored_from_history_id,
        old_snapshot=old_snapshot,
        old_evidence=old_evidence,
        new_snapshot=value,
        new_evidence=_dedupe_evidence(evidence),
        update_note=update_note,
    )


def _candidate_from_record(candidate: PinnedFactCandidate) -> DetectedCandidate:
    value = ValueSnapshot(
        kind=candidate.proposed_value_kind,
        text=candidate.proposed_value_text,
        json_value=candidate.proposed_value_json,
    )
    return DetectedCandidate(
        value=value,
        change_type=candidate.change_type,
        confidence=float(candidate.confidence or 0.0),
        evidence=_evidence_from_raw(candidate.evidence),
        source_document_id=candidate.source_document_id,
        idempotency_key=candidate.idempotency_key,
    )


def _persist_candidate(
    session: Session,
    *,
    fact: PinnedFact,
    detected: DetectedCandidate,
    status: str,
    review_notes: str | None = None,
    reviewed_by: UUID | None = None,
) -> PinnedFactCandidate:
    repo = PinnedFactsRepository(session)
    existing = repo.get_candidate_by_idempotency(fact.id, detected.idempotency_key)
    if existing is not None:
        return existing
    candidate = PinnedFactCandidate(
        pinned_fact_id=fact.id,
        space_id=fact.space_id,
        source_document_id=detected.source_document_id,
        proposed_value_kind=detected.value.kind,
        proposed_value_text=detected.value.text,
        proposed_value_json=detected.value.json_value,
        change_type=detected.change_type,
        confidence=detected.confidence,
        evidence=_raw_evidence(detected.evidence),
        status=status,
        idempotency_key=detected.idempotency_key,
        review_notes=review_notes,
        reviewed_by=reviewed_by,
        reviewed_at=utc_now() if reviewed_by is not None else None,
    )
    repo.add_candidate(candidate)
    session.flush()
    return candidate


def _resolve_pending_candidates(
    session: Session,
    *,
    fact_id: UUID,
    reviewed_by: UUID,
    keep_candidate_id: UUID | None,
    review_notes: str,
) -> None:
    reviewed_at = utc_now()
    for candidate in PinnedFactsRepository(session).list_candidates_for_fact(fact_id):
        if candidate.status != "pending" or candidate.id == keep_candidate_id:
            continue
        candidate.status = "rejected"
        candidate.review_notes = review_notes
        candidate.reviewed_by = reviewed_by
        candidate.reviewed_at = reviewed_at


def create_pinned_fact(session: Session, subject: str, *, space_scope: SpaceScope, payload) -> PinnedFact:
    owner_user_id = UUID(subject)
    space = resolve_single_owned_space(session, owner_user_id, space_scope)
    fact = PinnedFact(
        space_id=space.id,
        owner_user_id=owner_user_id,
        key=payload.key.strip(),
        title=payload.title.strip(),
        description=payload.description.strip(),
        entity_type_hint=payload.entity_type_hint.strip() if payload.entity_type_hint else None,
        is_active=payload.is_active,
        value_kind=payload.value_kind,
        value_text=payload.value_text,
        value_json=payload.value_json,
        status="active",
        confidence=payload.confidence,
        source_document_id=payload.source_document_id,
        evidence=_raw_evidence(_dedupe_evidence(payload.evidence)),
        last_checked_at=utc_now(),
    )
    repo = PinnedFactsRepository(session)
    repo.add_fact(fact)
    session.flush()
    _write_history(
        session,
        fact=fact,
        actor_user_id=owner_user_id,
        actor_type="user",
        reason="created",
        candidate_id=None,
        restored_from_history_id=None,
        old_snapshot=None,
        old_evidence=[],
        new_snapshot=ValueSnapshot(kind=payload.value_kind, text=payload.value_text, json_value=payload.value_json),
        new_evidence=_dedupe_evidence(payload.evidence),
        update_note=None,
    )
    record_change_event(
        session,
        space_id=fact.space_id,
        event_type="pinned_fact_created",
        title=f"Pinned fact created: {fact.title}",
        summary=f"{fact.title} was pinned with evidence.",
        actor_user_id=owner_user_id,
        pinned_fact_id=fact.id,
        payload={"value_kind": fact.value_kind},
    )
    session.commit()
    session.refresh(fact)
    return fact


def update_pinned_fact(session: Session, subject: str, fact: PinnedFact, *, payload) -> PinnedFact:
    changed = False
    if payload.title is not None:
        fact.title = payload.title.strip()
        changed = True
    if payload.description is not None:
        fact.description = payload.description.strip()
        changed = True
    if payload.entity_type_hint is not None:
        fact.entity_type_hint = payload.entity_type_hint.strip() or None
        changed = True
    if payload.is_active is not None:
        fact.is_active = payload.is_active
        changed = True
    if payload.value_kind is not None:
        next_value = build_value_snapshot(kind=payload.value_kind, text=payload.value_text, json_value=payload.value_json)
        next_evidence = _dedupe_evidence(payload.evidence) if payload.evidence is not None else _dedupe_evidence(_evidence_from_raw(fact.evidence))
        next_source_document_id = payload.source_document_id if payload.source_document_id is not None else fact.source_document_id
        next_confidence = payload.confidence if payload.confidence is not None else fact.confidence
        current_snapshot = _fact_snapshot(fact)
        current_evidence = _dedupe_evidence(_evidence_from_raw(fact.evidence))
        value_changed = current_snapshot is None or _value_signature(current_snapshot) != _value_signature(next_value)
        evidence_changed = _evidence_signature(current_evidence) != _evidence_signature(next_evidence)
        source_changed = fact.source_document_id != next_source_document_id
        confidence_changed = fact.confidence != next_confidence
        if value_changed or evidence_changed or source_changed or confidence_changed:
            _apply_fact_value(
                session,
                fact=fact,
                value=next_value,
                confidence=next_confidence,
                source_document_id=next_source_document_id,
                evidence=next_evidence,
                status="active",
                actor_user_id=UUID(subject),
                actor_type="user",
                reason="manual_edit",
                update_note=payload.update_note,
            )
            _resolve_pending_candidates(
                session,
                fact_id=fact.id,
                reviewed_by=UUID(subject),
                keep_candidate_id=None,
                review_notes="Superseded by a manual edit.",
            )
            changed = True
    if not changed:
        session.refresh(fact)
        return fact
    session.commit()
    session.refresh(fact)
    return fact


def _detect_candidates(
    results: list[SearchResult],
    current: ValueSnapshot | None,
    current_evidence: list[PinnedFactEvidence],
) -> tuple[str, list[DetectedCandidate], list[PinnedFactEvidence]]:
    evidence_items: list[PinnedFactEvidence] = []
    detected_by_value: dict[str, DetectedCandidate] = {}
    for result in results:
        detected = _detected_from_result(result)
        if detected is None:
            continue
        evidence_items.extend(detected.evidence)
        key = _value_signature(detected.value)
        existing = detected_by_value.get(key)
        if existing is None:
            detected_by_value[key] = detected
            continue
        merged_evidence = _dedupe_evidence([*existing.evidence, *detected.evidence])
        detected_by_value[key] = DetectedCandidate(
            value=existing.value,
            change_type=existing.change_type,
            confidence=max(existing.confidence, detected.confidence),
            evidence=merged_evidence,
            source_document_id=existing.source_document_id or detected.source_document_id,
            idempotency_key=f"{existing.source_document_id or detected.source_document_id}:{key}:{_evidence_signature(merged_evidence)}",
        )
    detected_items = list(detected_by_value.values())
    evidence_items = _dedupe_evidence(evidence_items)
    if not detected_items:
        return ("missing_evidence" if current is not None else "unknown"), [], []
    if current is not None and len(detected_items) == 1 and _value_signature(detected_items[0].value) == _value_signature(current):
        if _evidence_signature(detected_items[0].evidence) != _evidence_signature(current_evidence):
            current_item = detected_items[0]
            return (
                "evidence_update",
                [
                    DetectedCandidate(
                        value=current_item.value,
                        change_type="evidence_update",
                        confidence=current_item.confidence,
                        evidence=current_item.evidence,
                        source_document_id=current_item.source_document_id,
                        idempotency_key=current_item.idempotency_key,
                    )
                ],
                detected_items[0].evidence,
            )
        return "same", [], detected_items[0].evidence
    if len(detected_items) > 1:
        return "conflict", [DetectedCandidate(**{**item.__dict__, "change_type": "conflict", "confidence": min(item.confidence, 0.75)}) for item in detected_items], evidence_items
    return "update", detected_items, detected_items[0].evidence


def recheck_pinned_fact(
    session: Session,
    subject: str,
    fact: PinnedFact,
    *,
    document_id: UUID | None = None,
) -> PinnedFactDetail:
    results = retrieve_search_results(
        session,
        subject,
        space_scope=SpaceScope(space_id=fact.space_id),
        query_text=fact.description,
        mode=SearchMode.COMBINED,
        document_id=document_id,
        entity_type=fact.entity_type_hint,
        limit=5,
    )
    current = _fact_snapshot(fact)
    current_evidence = _dedupe_evidence(_evidence_from_raw(fact.evidence))
    decision, detected_items, supporting_evidence = _detect_candidates(results, current, current_evidence)
    actor_user_id = UUID(subject)
    fact.last_checked_at = utc_now()

    if decision == "unknown":
        fact.status = "unknown" if current is None else "active"
    elif decision == "missing_evidence":
        fact.status = "missing_evidence"
        record_change_event(
            session,
            space_id=fact.space_id,
            event_type="pinned_fact_missing_evidence",
            title=f"Pinned fact missing evidence: {fact.title}",
            summary=f"No supporting evidence was found for the current value of {fact.title}.",
            actor_user_id=actor_user_id,
            pinned_fact_id=fact.id,
        )
    elif decision == "same":
        fact.status = "active"
        if supporting_evidence and _evidence_signature(supporting_evidence) != _evidence_signature(current_evidence):
            fact.evidence = _raw_evidence(supporting_evidence)
    elif decision == "conflict":
        fact.status = "conflicted"
        for detected in detected_items:
            _persist_candidate(session, fact=fact, detected=detected, status="pending")
        record_change_event(
            session,
            space_id=fact.space_id,
            event_type="pinned_fact_conflict_detected",
            title=f"Pinned fact conflict: {fact.title}",
            summary=f"Multiple candidate values were found for {fact.title}.",
            actor_user_id=actor_user_id,
            pinned_fact_id=fact.id,
            payload={"candidate_count": len(detected_items)},
        )
    else:
        detected = detected_items[0]
        _persist_candidate(session, fact=fact, detected=detected, status="pending")
        fact.status = "pending_update"
        record_change_event(
            session,
            space_id=fact.space_id,
            event_type="pinned_fact_update_detected",
            title=f"Pinned fact update detected: {fact.title}",
            summary=(
                f"Updated evidence was found for {fact.title}."
                if decision == "evidence_update"
                else f"A new candidate value was found for {fact.title}."
            ),
            actor_user_id=actor_user_id,
            pinned_fact_id=fact.id,
            payload={"change_type": decision, "value_kind": detected.value.kind},
        )

    session.commit()
    session.refresh(fact)
    return build_fact_detail(session, fact)


def accept_pinned_fact_candidate(
    session: Session,
    subject: str,
    candidate: PinnedFactCandidate,
    *,
    override_value: ValueSnapshot | None,
    review_notes: str | None,
) -> PinnedFact:
    fact = session.get(PinnedFact, candidate.pinned_fact_id)
    assert fact is not None
    actor_user_id = UUID(subject)
    accepted = override_value or _candidate_from_record(candidate).value
    evidence = _evidence_from_raw(candidate.evidence)
    reason = "candidate_edited_accepted" if override_value is not None else "candidate_accepted"
    _apply_fact_value(
        session,
        fact=fact,
        value=accepted,
        confidence=candidate.confidence,
        source_document_id=candidate.source_document_id,
        evidence=evidence,
        status="active",
        actor_user_id=actor_user_id,
        actor_type="user",
        reason=reason,
        candidate_id=candidate.id,
        update_note=review_notes,
    )
    candidate.status = "accepted"
    candidate.review_notes = review_notes.strip() if review_notes else None
    candidate.reviewed_by = actor_user_id
    candidate.reviewed_at = utc_now()
    _resolve_pending_candidates(
        session,
        fact_id=fact.id,
        reviewed_by=actor_user_id,
        keep_candidate_id=candidate.id,
        review_notes="Superseded by an accepted update.",
    )
    record_change_event(
        session,
        space_id=fact.space_id,
        event_type="pinned_fact_candidate_accepted",
        title=f"Pinned fact review: {fact.title}",
        summary=f"A pending candidate for {fact.title} was accepted.",
        actor_user_id=actor_user_id,
        pinned_fact_id=fact.id,
        payload={"candidate_id": str(candidate.id)},
    )
    session.commit()
    session.refresh(fact)
    return fact


def reject_pinned_fact_candidate(session: Session, subject: str, candidate: PinnedFactCandidate, *, review_notes: str | None) -> PinnedFactCandidate:
    fact = session.get(PinnedFact, candidate.pinned_fact_id)
    assert fact is not None
    candidate.status = "rejected"
    candidate.review_notes = review_notes.strip() if review_notes else None
    candidate.reviewed_by = UUID(subject)
    candidate.reviewed_at = utc_now()
    remaining_pending = [
        item
        for item in PinnedFactsRepository(session).list_candidates_for_fact(candidate.pinned_fact_id)
        if item.id != candidate.id and item.status == "pending"
    ]
    if remaining_pending:
        fact.status = "conflicted" if any(item.change_type == "conflict" for item in remaining_pending) else "pending_update"
    else:
        fact.status = "active"
    session.commit()
    session.refresh(candidate)
    return candidate


def revert_pinned_fact_to_history(session: Session, subject: str, fact: PinnedFact, history: PinnedFactHistory) -> PinnedFact:
    actor_user_id = UUID(subject)
    target = ValueSnapshot(kind=history.new_value_kind, text=history.new_value_text, json_value=history.new_value_json)
    evidence = _evidence_from_raw(history.new_evidence)
    _apply_fact_value(
        session,
        fact=fact,
        value=target,
        confidence=fact.confidence,
        source_document_id=fact.source_document_id,
        evidence=evidence,
        status="active",
        actor_user_id=actor_user_id,
        actor_type="user",
        reason="user_reverted",
        restored_from_history_id=history.id,
        update_note=history.update_note,
    )
    _resolve_pending_candidates(
        session,
        fact_id=fact.id,
        reviewed_by=actor_user_id,
        keep_candidate_id=None,
        review_notes="Superseded by a restored historical version.",
    )
    record_change_event(
        session,
        space_id=fact.space_id,
        event_type="pinned_fact_reverted",
        title=f"Pinned fact reverted: {fact.title}",
        summary=f"{fact.title} was restored to an older version.",
        actor_user_id=actor_user_id,
        pinned_fact_id=fact.id,
        payload={"history_id": str(history.id)},
    )
    session.commit()
    session.refresh(fact)
    return fact


def apply_verified_correction_to_fact(session: Session, subject: str, fact: PinnedFact, correction: CorrectionRecord) -> PinnedFact:
    actor_user_id = UUID(subject)
    detected = DetectedCandidate(
        value=ValueSnapshot(kind="text", text=correction.proposed_value.strip(), json_value=None),
        change_type="update",
        confidence=1.0,
        evidence=[
            PinnedFactEvidence(
                quote=correction.proposed_value.strip(),
                citations=[correction_citation(correction, source_tier=SourceTier.VERIFIED)],
                source_chunk_ids=[],
            )
        ],
        source_document_id=correction.document_id,
        idempotency_key=f"correction:{correction.id}",
    )
    candidate = _persist_candidate(
        session,
        fact=fact,
        detected=detected,
        status="accepted",
        review_notes=correction.review_notes,
        reviewed_by=actor_user_id,
    )
    _apply_fact_value(
        session,
        fact=fact,
        value=detected.value,
        confidence=1.0,
        source_document_id=detected.source_document_id,
        evidence=detected.evidence,
        status="active",
        actor_user_id=actor_user_id,
        actor_type="user",
        reason="verified_correction",
        candidate_id=candidate.id,
        update_note=correction.review_notes,
    )
    _resolve_pending_candidates(
        session,
        fact_id=fact.id,
        reviewed_by=actor_user_id,
        keep_candidate_id=candidate.id,
        review_notes="Superseded by a verified correction.",
    )
    session.commit()
    session.refresh(fact)
    return fact


def build_value_snapshot(*, kind: str, text: str | None, json_value: dict[str, Any] | None) -> ValueSnapshot:
    return ValueSnapshot(kind=kind, text=text, json_value=json_value)


def recheck_space_facts(session: Session, subject: str, *, space_id: UUID, document_id: UUID | None = None) -> None:
    repo = PinnedFactsRepository(session)
    for fact in repo.list_active_facts_for_space(space_id):
        recheck_pinned_fact(session, subject, fact, document_id=document_id)
