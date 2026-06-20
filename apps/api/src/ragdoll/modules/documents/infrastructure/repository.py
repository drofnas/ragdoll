from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError
from ragdoll.core.pagination import PaginationParams
from ragdoll.platform.db.models import Document, Space


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DocumentListFilters:
    date_from: datetime | None = None
    date_to: datetime | None = None
    file_type: str | None = None
    uploaded_by: UUID | None = None


class DocumentsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _visible_stmt(self, owner_user_id: UUID):
        return (
            select(Document)
            .join(Space, Document.space_id == Space.id)
            .where(
                Space.owner_user_id == owner_user_id,
                Document.deleted_at.is_(None),
            )
        )

    def list_visible(
        self,
        owner_user_id: UUID,
        pagination: PaginationParams,
        *,
        filters: DocumentListFilters,
        space_id: UUID | None = None,
    ) -> tuple[list[Document], int]:
        stmt = self._visible_stmt(owner_user_id)
        if space_id is not None:
            stmt = stmt.where(Document.space_id == space_id)
        if filters.date_from is not None:
            stmt = stmt.where(Document.created_at >= filters.date_from)
        if filters.date_to is not None:
            stmt = stmt.where(Document.created_at <= filters.date_to)
        if filters.file_type is not None:
            stmt = stmt.where(Document.file_type == filters.file_type)
        if filters.uploaded_by is not None:
            stmt = stmt.where(Document.uploaded_by == filters.uploaded_by)

        total = self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        items = list(
            self.session.scalars(
                stmt.order_by(Document.created_at.desc())
                .offset(pagination.offset)
                .limit(pagination.page_size)
            )
        )
        return items, int(total)

    def get_visible_or_404(self, owner_user_id: UUID, document_id: UUID) -> Document:
        stmt = self._visible_stmt(owner_user_id).where(Document.id == document_id)
        document = self.session.scalar(stmt)
        if document is None:
            raise ApplicationError(
                "Requested document was not found.",
                status_code=404,
                title="Not found",
                type_uri="https://ragdoll.dev/problems/not-found",
                code="document_not_found",
            )
        return document

    def soft_delete(self, document: Document) -> None:
        document.deleted_at = utc_now()

