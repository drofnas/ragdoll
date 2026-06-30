from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError
from ragdoll.platform.db.models import ChangeEvent, ChangeEventRead


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChangesRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_event(self, event: ChangeEvent) -> None:
        self.session.add(event)

    def list_events(self, space_ids: list[UUID], *, since: datetime | None = None) -> list[ChangeEvent]:
        stmt = select(ChangeEvent).where(ChangeEvent.space_id.in_(space_ids))
        if since is not None:
            stmt = stmt.where(ChangeEvent.created_at >= since)
        stmt = stmt.order_by(ChangeEvent.created_at.desc())
        return list(self.session.scalars(stmt))

    def get_event_or_404(self, space_ids: list[UUID], change_id: UUID) -> ChangeEvent:
        stmt = select(ChangeEvent).where(ChangeEvent.id == change_id, ChangeEvent.space_id.in_(space_ids))
        event = self.session.scalar(stmt)
        if event is None:
            raise ApplicationError(
                "Requested change event was not found.",
                status_code=404,
                title="Not found",
                type_uri="https://ragdoll.dev/problems/not-found",
                code="change_not_found",
            )
        return event

    def get_read_map(self, *, user_id: UUID, change_ids: list[UUID]) -> dict[UUID, ChangeEventRead]:
        if not change_ids:
            return {}
        stmt = select(ChangeEventRead).where(
            ChangeEventRead.user_id == user_id,
            ChangeEventRead.change_event_id.in_(change_ids),
        )
        return {row.change_event_id: row for row in self.session.scalars(stmt)}

    def mark_read(self, *, change_event_id: UUID, user_id: UUID) -> ChangeEventRead:
        stmt = select(ChangeEventRead).where(
            ChangeEventRead.change_event_id == change_event_id,
            ChangeEventRead.user_id == user_id,
        )
        row = self.session.scalar(stmt)
        if row is None:
            row = ChangeEventRead(change_event_id=change_event_id, user_id=user_id)
            self.session.add(row)
        else:
            row.read_at = utc_now()
        self.session.commit()
        self.session.refresh(row)
        return row
