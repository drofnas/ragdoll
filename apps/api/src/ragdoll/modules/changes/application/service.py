from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.platform.db.models import ChangeEvent

from ragdoll.modules.changes.infrastructure.repository import ChangesRepository


def record_change_event(
    session: Session,
    *,
    space_id: UUID,
    event_type: str,
    title: str,
    summary: str,
    actor_user_id: UUID | None = None,
    document_id: UUID | None = None,
    tracked_field_id: UUID | None = None,
    correction_id: UUID | None = None,
    chat_session_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> ChangeEvent:
    event = ChangeEvent(
        space_id=space_id,
        event_type=event_type,
        title=title,
        summary=summary,
        actor_user_id=actor_user_id,
        document_id=document_id,
        tracked_field_id=tracked_field_id,
        correction_id=correction_id,
        chat_session_id=chat_session_id,
        payload=payload,
    )
    ChangesRepository(session).add_event(event)
    session.flush()
    return event
