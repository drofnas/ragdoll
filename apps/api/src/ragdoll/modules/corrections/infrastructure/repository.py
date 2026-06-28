from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError
from ragdoll.platform.db.models import CorrectionRecord


class CorrectionsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, correction: CorrectionRecord) -> None:
        self.session.add(correction)

    def list_visible(self, space_ids: list[UUID], *, status: str | None = None) -> list[CorrectionRecord]:
        stmt = (
            select(CorrectionRecord)
            .where(CorrectionRecord.space_id.in_(space_ids))
            .order_by(CorrectionRecord.created_at.desc())
        )
        if status is not None:
            stmt = stmt.where(CorrectionRecord.status == status)
        return list(self.session.scalars(stmt))

    def get_visible_or_404(self, space_ids: list[UUID], correction_id: UUID) -> CorrectionRecord:
        stmt = select(CorrectionRecord).where(
            CorrectionRecord.id == correction_id,
            CorrectionRecord.space_id.in_(space_ids),
        )
        correction = self.session.scalar(stmt)
        if correction is None:
            raise ApplicationError(
                "Requested correction was not found.",
                status_code=404,
                title="Not found",
                type_uri="https://ragdoll.dev/problems/not-found",
                code="correction_not_found",
            )
        return correction

    def list_verified_for_space(self, space_id: UUID) -> list[CorrectionRecord]:
        stmt = (
            select(CorrectionRecord)
            .where(CorrectionRecord.space_id == space_id, CorrectionRecord.status == "verified")
            .order_by(CorrectionRecord.reviewed_at.desc(), CorrectionRecord.created_at.desc())
        )
        return list(self.session.scalars(stmt))
