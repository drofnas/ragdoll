from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.core.pagination import PaginationParams
from ragdoll.modules.changes.api.schemas import ChangeEventDetail, ChangeEventReadResult, ChangeEventSummary, ChangeListResponse
from ragdoll.modules.changes.infrastructure.repository import ChangesRepository
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _build_summary(event, *, is_read: bool) -> ChangeEventSummary:
    return ChangeEventSummary(
        id=event.id,
        space_id=event.space_id,
        event_type=event.event_type,
        title=event.title,
        summary=event.summary,
        document_id=event.document_id,
        pinned_fact_id=event.pinned_fact_id,
        correction_id=event.correction_id,
        chat_session_id=event.chat_session_id,
        created_at=event.created_at,
        is_read=is_read,
    )


def list_changes(
    session: Session,
    subject: str,
    pagination: PaginationParams,
    *,
    space_scope: SpaceScope,
) -> ChangeListResponse:
    user_id = UUID(subject)
    repo = ChangesRepository(session)
    space_ids = resolve_owned_space_ids(session, user_id, space_scope)
    since = utc_now() - timedelta(days=30)
    events = repo.list_events(space_ids, since=since)
    reads = repo.get_read_map(user_id=user_id, change_ids=[event.id for event in events])
    total = len(events)
    page_events = events[pagination.offset : pagination.offset + pagination.page_size]
    return ChangeListResponse(
        items=[_build_summary(event, is_read=event.id in reads) for event in page_events],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_change_detail(session: Session, subject: str, change_id: UUID) -> ChangeEventDetail:
    user_id = UUID(subject)
    repo = ChangesRepository(session)
    event = repo.get_event_or_404(resolve_owned_space_ids(session, user_id, SpaceScope(all_spaces=True)), change_id)
    reads = repo.get_read_map(user_id=user_id, change_ids=[event.id])
    return ChangeEventDetail(**_build_summary(event, is_read=event.id in reads).model_dump(), payload=event.payload)


def mark_change_read(session: Session, subject: str, change_id: UUID) -> ChangeEventReadResult:
    user_id = UUID(subject)
    repo = ChangesRepository(session)
    repo.get_event_or_404(resolve_owned_space_ids(session, user_id, SpaceScope(all_spaces=True)), change_id)
    row = repo.mark_read(change_event_id=change_id, user_id=user_id)
    return ChangeEventReadResult(change_event_id=change_id, read_at=row.read_at)
