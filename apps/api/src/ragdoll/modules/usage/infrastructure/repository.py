from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ragdoll.platform.db.models import Document, Space, UsageEvent, UserUsageSnapshot


class UsageRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_snapshot(self, user_id: UUID) -> UserUsageSnapshot | None:
        return self.session.get(UserUsageSnapshot, user_id)

    def get_or_create_snapshot(self, user_id: UUID) -> UserUsageSnapshot:
        snapshot = self.get_snapshot(user_id)
        if snapshot is None:
            snapshot = UserUsageSnapshot(user_id=user_id)
            self.session.add(snapshot)
            self.session.flush()
        return snapshot

    def owned_document_metrics(self, user_id: UUID) -> tuple[int, int, int, int]:
        stmt = (
            select(Document)
            .join(Space, Document.space_id == Space.id)
            .where(
                Space.owner_user_id == user_id,
                Document.deleted_at.is_(None),
            )
        )
        documents = list(self.session.scalars(stmt))
        return (
            len(documents),
            sum(document.chunk_count for document in documents),
            sum(document.file_size for document in documents),
            sum(1 for document in documents if (document.processing_status or {}).get("overall") != "completed"),
        )

    def usage_total_since(self, user_id: UUID, event_type: str, since: datetime) -> int:
        stmt = (
            select(func.coalesce(func.sum(UsageEvent.quantity), 0))
            .where(
                UsageEvent.user_id == user_id,
                UsageEvent.event_type == event_type,
                UsageEvent.occurred_at >= since,
            )
        )
        return int(self.session.scalar(stmt) or 0)

    def earliest_usage_since(self, user_id: UUID, event_type: str, since: datetime) -> datetime | None:
        stmt = (
            select(func.min(UsageEvent.occurred_at))
            .where(
                UsageEvent.user_id == user_id,
                UsageEvent.event_type == event_type,
                UsageEvent.occurred_at >= since,
            )
        )
        return self.session.scalar(stmt)
