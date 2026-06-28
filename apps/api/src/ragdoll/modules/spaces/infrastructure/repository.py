from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError
from ragdoll.platform.db.models import Document, Space, TrackedField


SpaceCountRow = tuple[Space, int, int]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SpacesRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, space: Space) -> None:
        self.session.add(space)

    def list_by_owner(self, owner_user_id: UUID, *, include_archived: bool) -> list[Space]:
        stmt = select(Space).where(Space.owner_user_id == owner_user_id).order_by(
            Space.is_default.desc(),
            Space.created_at.asc(),
        )
        if not include_archived:
            stmt = stmt.where(Space.archived_at.is_(None))
        return list(self.session.scalars(stmt))

    def list_by_owner_with_counts(self, owner_user_id: UUID, *, include_archived: bool) -> list[SpaceCountRow]:
        document_counts = (
            select(
                Document.space_id.label("space_id"),
                func.count(Document.id).label("document_count"),
            )
            .where(Document.deleted_at.is_(None))
            .group_by(Document.space_id)
            .subquery()
        )
        tracked_field_counts = (
            select(
                TrackedField.space_id.label("space_id"),
                func.count(TrackedField.id).label("tracked_field_count"),
            )
            .group_by(TrackedField.space_id)
            .subquery()
        )
        stmt = (
            select(
                Space,
                func.coalesce(document_counts.c.document_count, 0),
                func.coalesce(tracked_field_counts.c.tracked_field_count, 0),
            )
            .outerjoin(document_counts, document_counts.c.space_id == Space.id)
            .outerjoin(tracked_field_counts, tracked_field_counts.c.space_id == Space.id)
            .where(Space.owner_user_id == owner_user_id)
            .order_by(
                Space.is_default.desc(),
                Space.created_at.asc(),
            )
        )
        if not include_archived:
            stmt = stmt.where(Space.archived_at.is_(None))
        return [
            (space, int(document_count), int(tracked_field_count))
            for space, document_count, tracked_field_count in self.session.execute(stmt)
        ]

    def counts_for_space(self, space_id: UUID) -> tuple[int, int]:
        document_count = self.session.scalar(
            select(func.count(Document.id)).where(
                Document.space_id == space_id,
                Document.deleted_at.is_(None),
            )
        )
        tracked_field_count = self.session.scalar(
            select(func.count(TrackedField.id)).where(TrackedField.space_id == space_id)
        )
        return int(document_count or 0), int(tracked_field_count or 0)

    def get_owned_or_404(self, owner_user_id: UUID, space_id: UUID) -> Space:
        stmt = select(Space).where(
            Space.id == space_id,
            Space.owner_user_id == owner_user_id,
        )
        space = self.session.scalar(stmt)
        if space is None:
            raise ApplicationError(
                "Requested space was not found.",
                status_code=404,
                title="Not found",
                type_uri="https://ragdoll.dev/problems/not-found",
                code="space_not_found",
            )
        return space

    def get_default_owned_space_or_404(self, owner_user_id: UUID) -> Space:
        stmt = select(Space).where(
            Space.owner_user_id == owner_user_id,
            Space.is_default.is_(True),
            Space.archived_at.is_(None),
        )
        space = self.session.scalar(stmt)
        if space is None:
            raise ApplicationError(
                "An active default space is required before uploading documents.",
                status_code=409,
                title="Conflict",
                type_uri="https://ragdoll.dev/problems/conflict",
                code="default_space_required",
            )
        return space

    def list_active_owned_space_ids(self, owner_user_id: UUID) -> list[UUID]:
        stmt = select(Space.id).where(
            Space.owner_user_id == owner_user_id,
            Space.archived_at.is_(None),
        )
        return list(self.session.scalars(stmt))

    def clear_default_for_owner(self, owner_user_id: UUID, *, exclude_space_id: UUID) -> None:
        stmt = select(Space).where(
            Space.owner_user_id == owner_user_id,
            Space.id != exclude_space_id,
            Space.is_default.is_(True),
        )
        for space in self.session.scalars(stmt):
            space.is_default = False

    def archive(self, space: Space) -> None:
        if space.archived_at is None:
            space.archived_at = utc_now()

    def unarchive(self, space: Space) -> None:
        space.archived_at = None
