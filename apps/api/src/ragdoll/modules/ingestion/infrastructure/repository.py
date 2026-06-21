from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ragdoll.platform.db.models import Document, DocumentChunk, DocumentProcessingJob, Space


@dataclass(frozen=True)
class VisibleStatusRecord:
    document: Document
    latest_job: DocumentProcessingJob | None


class IngestionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_document(self, document: Document) -> None:
        self.session.add(document)

    def add_processing_job(self, job: DocumentProcessingJob) -> None:
        self.session.add(job)

    def latest_job_for_document(self, document_id: UUID) -> DocumentProcessingJob | None:
        return self.session.scalar(
            select(DocumentProcessingJob)
            .where(DocumentProcessingJob.document_id == document_id)
            .order_by(DocumentProcessingJob.queued_at.desc())
            .limit(1)
        )

    def list_visible_statuses(self, owner_user_id: UUID, document_ids: list[UUID]) -> list[VisibleStatusRecord]:
        if not document_ids:
            return []
        documents = list(
            self.session.scalars(
                select(Document)
                .join(Space, Document.space_id == Space.id)
                .where(
                    Space.owner_user_id == owner_user_id,
                    Document.deleted_at.is_(None),
                    Document.id.in_(document_ids),
                )
            )
        )
        if not documents:
            return []
        latest_jobs = {
            document.id: self.latest_job_for_document(document.id)
            for document in documents
        }
        by_id = {document.id: document for document in documents}
        return [
            VisibleStatusRecord(document=by_id[document_id], latest_job=latest_jobs[document_id])
            for document_id in document_ids
            if document_id in by_id
        ]

    def replace_chunks(self, document: Document, chunks: list[DocumentChunk]) -> None:
        self.session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        for chunk in chunks:
            self.session.add(chunk)
