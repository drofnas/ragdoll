from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError
from ragdoll.platform.db.models import CorrectionRecord, TrackedField, TrackedFieldValue


class TrackedStateRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_field(self, field: TrackedField) -> None:
        self.session.add(field)

    def list_fields(self, space_ids: list[UUID]) -> list[TrackedField]:
        stmt = (
            select(TrackedField)
            .where(TrackedField.space_id.in_(space_ids))
            .order_by(TrackedField.created_at.asc(), TrackedField.key.asc())
        )
        return list(self.session.scalars(stmt))

    def list_active_fields(self, space_ids: list[UUID]) -> list[TrackedField]:
        stmt = (
            select(TrackedField)
            .where(TrackedField.space_id.in_(space_ids), TrackedField.is_active.is_(True))
            .order_by(TrackedField.created_at.asc(), TrackedField.key.asc())
        )
        return list(self.session.scalars(stmt))

    def list_active_fields_for_space(self, space_id: UUID) -> list[TrackedField]:
        stmt = (
            select(TrackedField)
            .where(TrackedField.space_id == space_id, TrackedField.is_active.is_(True))
            .order_by(TrackedField.created_at.asc(), TrackedField.key.asc())
        )
        return list(self.session.scalars(stmt))

    def get_visible_or_404(self, space_ids: list[UUID], field_id: UUID) -> TrackedField:
        stmt = select(TrackedField).where(TrackedField.id == field_id, TrackedField.space_id.in_(space_ids))
        field = self.session.scalar(stmt)
        if field is None:
            raise ApplicationError(
                "Requested tracked field was not found.",
                status_code=404,
                title="Not found",
                type_uri="https://ragdoll.dev/problems/not-found",
                code="tracked_field_not_found",
            )
        return field

    def get_current_value(self, field_id: UUID) -> TrackedFieldValue | None:
        stmt = select(TrackedFieldValue).where(
            TrackedFieldValue.tracked_field_id == field_id,
            TrackedFieldValue.is_current.is_(True),
        )
        return self.session.scalar(stmt)

    def clear_current_value(self, field_id: UUID) -> None:
        stmt = select(TrackedFieldValue).where(
            TrackedFieldValue.tracked_field_id == field_id,
            TrackedFieldValue.is_current.is_(True),
        )
        for row in self.session.scalars(stmt):
            row.is_current = False

    def add_value(self, value: TrackedFieldValue) -> None:
        self.session.add(value)

    def list_corrections(self, field_id: UUID) -> list[CorrectionRecord]:
        stmt = (
            select(CorrectionRecord)
            .where(CorrectionRecord.tracked_field_id == field_id)
            .order_by(CorrectionRecord.created_at.desc())
        )
        return list(self.session.scalars(stmt))
