from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError
from ragdoll.platform.db.models import Space


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
