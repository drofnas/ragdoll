from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.modules.ingestion.domain.policies import (
    build_preview_text,
    chunk_text,
    extract_text_content,
    limit_chunks_for_plan,
    mark_processing_completed,
    mark_processing_failed,
    mark_processing_started,
)
from ragdoll.modules.ingestion.infrastructure.repository import IngestionRepository
from ragdoll.modules.users.application.queries import get_user_by_subject
from ragdoll.platform.db.models import Document, DocumentChunk
from ragdoll.platform.db.session import get_session_factory
from ragdoll.platform.queues import DocumentProcessingQueueService, ProcessingJobPayload
from ragdoll.platform.storage import DocumentStorageService, get_document_storage


def _build_document_chunks(document: Document, *, text: str, plan_tier: str) -> tuple[int, list[DocumentChunk]]:
    raw_chunks = chunk_text(text)
    limited_chunks = limit_chunks_for_plan(raw_chunks, plan_tier=plan_tier)
    rows = [
        DocumentChunk.from_text(
            document_id=document.id,
            space_id=document.space_id,
            chunk_index=index,
            text_content=chunk,
        )
        for index, chunk in enumerate(limited_chunks)
    ]
    return len(raw_chunks), rows


def _load_document(session: Session, document_id: UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise FileNotFoundError(f"Document {document_id} was not found.")
    return document


def process_job_payload(
    payload: ProcessingJobPayload,
    queue: DocumentProcessingQueueService,
    *,
    storage: DocumentStorageService | None = None,
) -> None:
    session = get_session_factory()()
    active_storage = storage or get_document_storage()

    try:
        document = _load_document(session, payload.document_id)
        if payload.requested_stage != "parsing":
            raise ValueError(f"Unsupported processing stage: {payload.requested_stage}")

        document.processing_status = mark_processing_started(document.processing_status)
        session.commit()

        blob = active_storage.download_original_file(document.storage_key)
        extracted_text = extract_text_content(file_type=document.file_type, content=blob)
        user = get_user_by_subject(session, str(document.uploaded_by))
        total_chunks, chunk_rows = _build_document_chunks(document, text=extracted_text, plan_tier=user.plan_tier)

        repo = IngestionRepository(session)
        repo.replace_chunks(document, chunk_rows)
        document.preview_text = build_preview_text(extracted_text)
        document.original_text_content = extracted_text
        document.chunk_count = total_chunks
        document.indexed_chunk_count = len(chunk_rows)
        document.processing_status = mark_processing_completed(document.processing_status)
        session.commit()
        queue.mark_job_completed(payload.job_id)
    except Exception as exc:
        document = session.get(Document, payload.document_id)
        if document is not None:
            document.processing_status = mark_processing_failed(document.processing_status, str(exc))
            session.commit()
        queue.mark_job_failed(payload.job_id, str(exc))
    finally:
        session.close()
