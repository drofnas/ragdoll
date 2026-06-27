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
    mark_processing_stage_failed,
    reset_processing_status_for_stage,
    validate_requested_stage,
)
from ragdoll.modules.ingestion.infrastructure.repository import IngestionRepository
from ragdoll.modules.spaces.infrastructure.repository import SpacesRepository
from ragdoll.modules.usage.infrastructure.repository import UsageRepository
from ragdoll.platform.db.models import Document, DocumentChunk, DocumentProcessingJob
from ragdoll.platform.graph import GraphCleanupService
from ragdoll.platform.queues import (
    DocumentProcessingQueueService,
    ProcessingJobPayload,
    reconcile_stale_processing_jobs,
    utc_now,
)
from ragdoll.platform.storage import DocumentStorageService
from ragdoll.platform.vector import VectorCleanupService


def resolve_target_space(session: Session, owner_user_id: UUID, space_id: UUID | None):
    repo = SpacesRepository(session)
    if space_id is None:
        return repo.get_default_owned_space_or_404(owner_user_id)
    space = repo.get_owned_or_404(owner_user_id, space_id)
    ensure_destination_space_accepts_documents(space)
    return space


def _build_job(
    document: Document,
    *,
    attempt: int,
    requested_stage: str,
    job_kind: str,
    cleanup_derived_artifacts: bool = False,
    reset_document_content: bool = False,
    clear_existing_chunks: bool = False,
    clear_existing_entities: bool = False,
    cleanup_vectors: bool = False,
    cleanup_graph: bool = False,
) -> DocumentProcessingJob:
    return DocumentProcessingJob(
        document_id=document.id,
        space_id=document.space_id,
        uploaded_by=document.uploaded_by,
        requested_stage=validate_requested_stage(requested_stage),
        job_kind=job_kind,
        status="queued",
        attempt=attempt,
        cleanup_derived_artifacts=cleanup_derived_artifacts,
        reset_document_content=reset_document_content,
        clear_existing_chunks=clear_existing_chunks,
        clear_existing_entities=clear_existing_entities,
        cleanup_vectors=cleanup_vectors,
        cleanup_graph=cleanup_graph,
    )


def _ensure_document_is_requeueable(active_job: DocumentProcessingJob | None, queued_job_count: int) -> None:
    if active_job is not None or queued_job_count > 0:
        raise ApplicationError(
            "This document already has active or queued processing work.",
            status_code=409,
            title="Conflict",
            type_uri="https://ragdoll.dev/problems/conflict",
            code="document_job_already_active",
        )


def _next_attempt(latest_job: DocumentProcessingJob | None) -> int:
    return 1 if latest_job is None else latest_job.attempt + 1


def _mark_enqueue_failed(
    session: Session,
    *,
    document: Document,
    job: DocumentProcessingJob,
    detail: str,
) -> None:
    job.status = "failed"
    job.completed_at = utc_now()
    job.visible_error_detail = detail[:2000]
    document.processing_status = mark_processing_stage_failed(
        document.processing_status,
        failed_stage=job.requested_stage,
        detail=detail,
    )
    session.commit()


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
    enforce_upload_size_limit(file_size=file_size)

    usage_repo = UsageRepository(session)
    document_count, _, storage_bytes, _ = usage_repo.owned_document_metrics(owner_user_id)
    enforce_document_limit(existing_document_count=document_count)
    enforce_storage_limit(
        existing_storage_bytes=storage_bytes,
        incoming_file_size=file_size,
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

    job = _build_job(document, attempt=1, requested_stage="parsing", job_kind="upload")
    repo.add_processing_job(job)
    session.commit()
    session.refresh(document)
    session.refresh(job)

    payload = ProcessingJobPayload(
        job_id=job.id,
        document_id=document.id,
        space_id=document.space_id,
        uploaded_by=document.uploaded_by,
        requested_stage=job.requested_stage,
        attempt=job.attempt,
        job_kind=job.job_kind,
        cleanup_derived_artifacts=job.cleanup_derived_artifacts,
        reset_document_content=job.reset_document_content,
        clear_existing_chunks=job.clear_existing_chunks,
        clear_existing_entities=job.clear_existing_entities,
        cleanup_vectors=job.cleanup_vectors,
        cleanup_graph=job.cleanup_graph,
    )
    try:
        queue.enqueue(payload)
    except Exception:
        _mark_enqueue_failed(
            session,
            document=document,
            job=job,
            detail="Document processing could not be queued because Redis or RQ was unavailable.",
        )
        raise
    return UploadDocumentResponse(
        document_id=document.id,
        job_id=job.id,
        filename=metadata.filename,
        processing_status=ProcessingStatus.model_validate(document.processing_status),
    )


def requeue_document_processing(
    session: Session,
    *,
    subject: str,
    document_id: UUID,
    queue: DocumentProcessingQueueService,
    requested_stage: str,
    reset_document_content: bool,
    clear_existing_chunks: bool,
    clear_existing_entities: bool,
    vector_cleanup: VectorCleanupService | None = None,
    graph_cleanup: GraphCleanupService | None = None,
) -> DocumentProcessingJob | None:
    owner_user_id = UUID(subject)
    document = DocumentsRepository(session).get_visible_or_404(owner_user_id, document_id)
    reconcile_stale_processing_jobs(session, document_ids=[document.id])
    repo = IngestionRepository(session)
    latest_job = repo.latest_job_for_document(document_id)
    active_job = repo.active_job_for_document(document_id)
    queued_job_count = repo.queued_job_count_for_document(document_id)
    stage = validate_requested_stage(requested_stage)
    job_kind = "reprocess" if reset_document_content and clear_existing_chunks else "retry"

    if job_kind == "reprocess":
        queued_reprocess = repo.queued_reprocess_for_document(document_id)
        if queued_reprocess is not None:
            return queued_reprocess
        if active_job is None and queued_job_count > 0:
            return None
    else:
        _ensure_document_is_requeueable(active_job, queued_job_count)
        document.processing_status = reset_processing_status_for_stage(document.processing_status, requested_stage=stage)
        if vector_cleanup is not None and stage == "vector":
            vector_cleanup.cleanup_document(document.id)
        if graph_cleanup is not None and stage in {"extraction", "graph"}:
            graph_cleanup.cleanup_document(document.id)
        if clear_existing_entities:
            repo.clear_entities_for_document(document.id)
            repo.prune_orphan_canonical_entities()
        if reset_document_content:
            document.preview_text = None
            document.original_text_content = None
            document.chunk_count = 0
            document.indexed_chunk_count = 0
        if clear_existing_chunks:
            session.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()

    job = _build_job(
        document,
        attempt=_next_attempt(latest_job),
        requested_stage=stage,
        job_kind=job_kind,
        cleanup_derived_artifacts=job_kind == "reprocess",
        reset_document_content=job_kind == "reprocess" and reset_document_content,
        clear_existing_chunks=job_kind == "reprocess" and clear_existing_chunks,
        clear_existing_entities=job_kind == "reprocess" and clear_existing_entities,
        cleanup_vectors=job_kind == "reprocess",
        cleanup_graph=job_kind == "reprocess",
    )
    repo.add_processing_job(job)
    session.commit()
    session.refresh(job)

    payload = ProcessingJobPayload(
        job_id=job.id,
        document_id=job.document_id,
        space_id=job.space_id,
        uploaded_by=job.uploaded_by,
        requested_stage=job.requested_stage,
        attempt=job.attempt,
        job_kind=job.job_kind,
        cleanup_derived_artifacts=job.cleanup_derived_artifacts,
        reset_document_content=job.reset_document_content,
        clear_existing_chunks=job.clear_existing_chunks,
        clear_existing_entities=job.clear_existing_entities,
        cleanup_vectors=job.cleanup_vectors,
        cleanup_graph=job.cleanup_graph,
    )
    try:
        queue.enqueue(payload)
    except Exception:
        _mark_enqueue_failed(
            session,
            document=document,
            job=job,
            detail="Document processing could not be queued because Redis or RQ was unavailable.",
        )
        raise
    return job
