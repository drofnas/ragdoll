from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import delete, exists, func, select
from sqlalchemy.orm import Session

from ragdoll.platform.db.models import (
    CanonicalEntity,
    Document,
    DocumentChunk,
    DocumentProcessingJob,
    Entity,
    GraphNode,
    Space,
)


@dataclass(frozen=True)
class VisibleStatusRecord:
    document: Document
    latest_job: DocumentProcessingJob | None
    active_job: DocumentProcessingJob | None
    queued_job_count: int
    has_queued_reprocess: bool


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

    def active_job_for_document(self, document_id: UUID) -> DocumentProcessingJob | None:
        return self.session.scalar(
            select(DocumentProcessingJob)
            .where(
                DocumentProcessingJob.document_id == document_id,
                DocumentProcessingJob.status == "processing",
            )
            .order_by(DocumentProcessingJob.started_at.desc(), DocumentProcessingJob.queued_at.desc())
            .limit(1)
        )

    def queued_job_count_for_document(self, document_id: UUID) -> int:
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(DocumentProcessingJob)
                .where(
                    DocumentProcessingJob.document_id == document_id,
                    DocumentProcessingJob.status == "queued",
                )
            )
            or 0
        )

    def has_queued_reprocess_for_document(self, document_id: UUID) -> bool:
        return bool(
            self.session.scalar(
                select(func.count())
                .select_from(DocumentProcessingJob)
                .where(
                    DocumentProcessingJob.document_id == document_id,
                    DocumentProcessingJob.status == "queued",
                    DocumentProcessingJob.job_kind == "reprocess",
                )
            )
            or 0
        )

    def queued_reprocess_for_document(self, document_id: UUID) -> DocumentProcessingJob | None:
        return self.session.scalar(
            select(DocumentProcessingJob)
            .where(
                DocumentProcessingJob.document_id == document_id,
                DocumentProcessingJob.status == "queued",
                DocumentProcessingJob.job_kind == "reprocess",
            )
            .order_by(DocumentProcessingJob.queued_at.asc())
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
        latest_jobs = {document.id: self.latest_job_for_document(document.id) for document in documents}
        active_jobs = {document.id: self.active_job_for_document(document.id) for document in documents}
        queued_counts = {document.id: self.queued_job_count_for_document(document.id) for document in documents}
        queued_reprocess_flags = {
            document.id: self.has_queued_reprocess_for_document(document.id)
            for document in documents
        }
        by_id = {document.id: document for document in documents}
        return [
            VisibleStatusRecord(
                document=by_id[document_id],
                latest_job=latest_jobs[document_id],
                active_job=active_jobs[document_id],
                queued_job_count=queued_counts[document_id],
                has_queued_reprocess=queued_reprocess_flags[document_id],
            )
            for document_id in document_ids
            if document_id in by_id
        ]

    def replace_chunks(self, document: Document, chunks: list[DocumentChunk]) -> None:
        self.session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        for chunk in chunks:
            self.session.add(chunk)

    def replace_entities(self, document: Document, entities: list[Entity]) -> None:
        self.session.execute(delete(Entity).where(Entity.document_id == document.id))
        for entity in entities:
            self.session.add(entity)

    def clear_entities_for_document(self, document_id: UUID) -> int:
        result = self.session.execute(delete(Entity).where(Entity.document_id == document_id))
        return int(result.rowcount or 0)

    def prune_orphan_canonical_entities(self) -> int:
        self.session.execute(
            delete(GraphNode).where(
                ~exists(select(Entity.id).where(Entity.canonical_entity_id == GraphNode.canonical_entity_id))
            )
        )
        result = self.session.execute(
            delete(CanonicalEntity).where(
                ~exists(select(Entity.id).where(Entity.canonical_entity_id == CanonicalEntity.id))
            )
        )
        return int(result.rowcount or 0)

    def get_or_create_canonical_entity(
        self,
        *,
        space_id: UUID,
        entity_type: str,
        normalized_name: str,
        display_name: str,
    ) -> CanonicalEntity:
        existing = self.session.scalar(
            select(CanonicalEntity).where(
                CanonicalEntity.space_id == space_id,
                CanonicalEntity.entity_type == entity_type,
                CanonicalEntity.normalized_name == normalized_name,
            )
        )
        if existing is not None:
            existing.display_name = display_name
            return existing

        canonical = CanonicalEntity(
            space_id=space_id,
            entity_type=entity_type,
            normalized_name=normalized_name,
            display_name=display_name,
        )
        self.session.add(canonical)
        self.session.flush()
        return canonical
