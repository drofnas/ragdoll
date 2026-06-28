from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.modules.documents.infrastructure.repository import DocumentsRepository
from ragdoll.modules.ingestion.api.schemas import (
    BatchDocumentStatusResponse,
    DocumentProcessingJobResponse,
    DocumentProcessingStatusResponse,
)
from ragdoll.modules.ingestion.domain.policies import dedupe_document_ids
from ragdoll.modules.ingestion.infrastructure.repository import IngestionRepository, VisibleStatusRecord
from ragdoll.platform.db.models import DocumentProcessingJob
from ragdoll.platform.queues import reconcile_stale_processing_jobs


def build_job_response(job: DocumentProcessingJob | None) -> DocumentProcessingJobResponse | None:
    if job is None:
        return None
    return DocumentProcessingJobResponse.model_validate(job)


def build_status_response(record: VisibleStatusRecord) -> DocumentProcessingStatusResponse:
    return DocumentProcessingStatusResponse(
        document_id=record.document.id,
        space_id=record.document.space_id,
        uploaded_by=record.document.uploaded_by,
        processing_status=record.document.processing_status,
        chunk_count=record.document.chunk_count,
        indexed_chunk_count=record.document.indexed_chunk_count,
        latest_job=build_job_response(record.latest_job),
        active_job=build_job_response(record.active_job),
        queued_job_count=record.queued_job_count,
        has_queued_reprocess=record.has_queued_reprocess,
        updated_at=record.document.updated_at,
    )


def get_document_status(session: Session, subject: str, document_id: UUID) -> DocumentProcessingStatusResponse:
    owner_user_id = UUID(subject)
    document = DocumentsRepository(session).get_visible_or_404(owner_user_id, document_id)
    reconcile_stale_processing_jobs(session, document_ids=[document.id])
    repo = IngestionRepository(session)
    latest_job = repo.latest_job_for_document(document_id)
    return build_status_response(
        VisibleStatusRecord(
            document=document,
            latest_job=latest_job,
            active_job=repo.active_job_for_document(document_id),
            queued_job_count=repo.queued_job_count_for_document(document_id),
            has_queued_reprocess=repo.has_queued_reprocess_for_document(document_id),
        )
    )


def get_batch_document_statuses(
    session: Session,
    subject: str,
    document_ids: list[UUID],
) -> BatchDocumentStatusResponse:
    owner_user_id = UUID(subject)
    unique_ids = dedupe_document_ids(document_ids)
    reconcile_stale_processing_jobs(session, document_ids=unique_ids)
    statuses = IngestionRepository(session).list_visible_statuses(owner_user_id, unique_ids)
    return BatchDocumentStatusResponse(statuses=[build_status_response(record) for record in statuses])
