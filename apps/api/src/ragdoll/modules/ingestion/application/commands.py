from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import ProcessingStatus
from ragdoll.core.auth import AuthenticatedPrincipal
from ragdoll.core.config import Settings
from ragdoll.core.exceptions import ApplicationError
from ragdoll.modules.documents.infrastructure.repository import DocumentsRepository
from ragdoll.modules.documents.domain.policies import ensure_destination_space_accepts_documents
from ragdoll.modules.ingestion.api.schemas import UploadDocumentResponse
from ragdoll.modules.ingestion.domain.policies import (
    build_processing_status_for_upload,
    build_storage_key,
    derive_upload_metadata,
    enforce_document_limit,
    enforce_storage_limit,
    enforce_upload_rate_limit,
    enforce_upload_size_limit,
)
from ragdoll.modules.ingestion.infrastructure.repository import IngestionRepository
from ragdoll.modules.spaces.infrastructure.repository import SpacesRepository
from ragdoll.modules.usage.infrastructure.repository import UsageRepository
from ragdoll.platform.db.models import Document, DocumentChunk, DocumentProcessingJob
from ragdoll.platform.queues import DocumentProcessingQueueService, ProcessingJobPayload
from ragdoll.platform.storage import DocumentStorageService


def resolve_target_space(session: Session, owner_user_id: UUID, space_id: UUID | None):
    repo = SpacesRepository(session)
    if space_id is None:
        return repo.get_default_owned_space_or_404(owner_user_id)
    space = repo.get_owned_or_404(owner_user_id, space_id)
    ensure_destination_space_accepts_documents(space)
    return space


def _build_job(document: Document, *, attempt: int) -> DocumentProcessingJob:
    return DocumentProcessingJob(
        document_id=document.id,
        space_id=document.space_id,
        uploaded_by=document.uploaded_by,
        requested_stage="parsing",
        status="queued",
        attempt=attempt,
    )


def _ensure_document_is_requeueable(job: DocumentProcessingJob | None) -> int:
    if job is not None and job.status in {"queued", "processing"}:
        raise ApplicationError(
            "This document already has an active processing job.",
            status_code=409,
            title="Conflict",
            type_uri="https://ragdoll.dev/problems/conflict",
            code="document_job_already_active",
        )
    return 1 if job is None else job.attempt + 1


def upload_document(
    session: Session,
    *,
    current_user: AuthenticatedPrincipal,
    settings: Settings,
    storage: DocumentStorageService,
    queue: DocumentProcessingQueueService,
    filename: str,
    content_type: str | None,
    content: bytes,
    space_id: UUID | None,
) -> UploadDocumentResponse:
    owner_user_id = UUID(current_user.subject)
    metadata = derive_upload_metadata(filename, content_type)
    file_size = len(content)

    enforce_upload_rate_limit(
        user_id=owner_user_id,
        enabled=settings.upload_rate_limit_enabled,
        max_requests=settings.upload_rate_limit_requests,
        window_seconds=settings.upload_rate_limit_window_seconds,
    )
    enforce_upload_size_limit(file_size=file_size, plan_tier=current_user.plan_tier)

    usage_repo = UsageRepository(session)
    document_count, _, storage_bytes, _ = usage_repo.owned_document_metrics(owner_user_id)
    enforce_document_limit(existing_document_count=document_count, plan_tier=current_user.plan_tier)
    enforce_storage_limit(
        existing_storage_bytes=storage_bytes,
        incoming_file_size=file_size,
        plan_tier=current_user.plan_tier,
    )

    target_space = resolve_target_space(session, owner_user_id, space_id)
    document_id = uuid4()
    storage_key = build_storage_key(
        owner_user_id=owner_user_id,
        space_id=target_space.id,
        document_id=document_id,
        safe_filename=metadata.filename,
    )

    storage.store_original_file(storage_key, content, content_type=metadata.mime_type)

    document = Document(
        id=document_id,
        space_id=target_space.id,
        uploaded_by=owner_user_id,
        title=metadata.filename,
        original_filename=metadata.filename,
        mime_type=metadata.mime_type,
        file_type=metadata.file_type,
        file_size=file_size,
        storage_key=storage_key,
        source_kind="manual_upload",
        processing_status=build_processing_status_for_upload(),
        chunk_count=0,
        indexed_chunk_count=0,
    )
    repo = IngestionRepository(session)
    repo.add_document(document)
    session.flush()

    job = _build_job(document, attempt=1)
    repo.add_processing_job(job)
    session.commit()
    session.refresh(document)
    session.refresh(job)

    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=document.space_id,
            uploaded_by=document.uploaded_by,
            requested_stage=job.requested_stage,
            attempt=job.attempt,
        )
    )
    return UploadDocumentResponse(
        document_id=document.id,
        job_id=job.id,
        filename=metadata.filename,
        processing_status=ProcessingStatus.model_validate(document.processing_status),
    )


def requeue_document_for_parsing(
    session: Session,
    *,
    subject: str,
    document_id: UUID,
    queue: DocumentProcessingQueueService,
    clear_existing_chunks: bool,
) -> DocumentProcessingJob:
    owner_user_id = UUID(subject)
    document = DocumentsRepository(session).get_visible_or_404(owner_user_id, document_id)
    latest_job = IngestionRepository(session).latest_job_for_document(document_id)
    attempt = _ensure_document_is_requeueable(latest_job)

    document.processing_status = build_processing_status_for_upload()
    document.preview_text = None
    document.original_text_content = None
    document.chunk_count = 0
    document.indexed_chunk_count = 0
    if clear_existing_chunks:
        session.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()

    job = _build_job(document, attempt=attempt)
    IngestionRepository(session).add_processing_job(job)
    session.commit()
    session.refresh(job)

    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=job.document_id,
            space_id=job.space_id,
            uploaded_by=job.uploaded_by,
            requested_stage=job.requested_stage,
            attempt=job.attempt,
        )
    )
    return job
