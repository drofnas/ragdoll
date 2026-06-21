from __future__ import annotations

from ragdoll.modules.ingestion.domain.policies import build_processing_status_for_upload
from ragdoll.platform.db.models import Document, DocumentChunk, DocumentProcessingJob, Space, User
from ragdoll.platform.queues import InMemoryDocumentProcessingQueue, ProcessingJobPayload, SqlDocumentProcessingQueue
from ragdoll.platform.storage import InMemoryDocumentStorage
from ragdoll.workers.document_pipeline import drain_document_jobs


def _seed_user_space_document(db_session):
    user = User(email="worker@example.com", hashed_password="hashed")
    db_session.add(user)
    db_session.flush()
    space = Space(owner_user_id=user.id, name="Default", description=None, is_default=True)
    db_session.add(space)
    db_session.flush()
    document = Document(
        space_id=space.id,
        uploaded_by=user.id,
        title="notes.txt",
        original_filename="notes.txt",
        mime_type="text/plain",
        file_type="txt",
        file_size=12,
        storage_key=f"documents/{user.id}/{space.id}/notes.txt",
        source_kind="manual_upload",
        processing_status=build_processing_status_for_upload(),
    )
    db_session.add(document)
    db_session.flush()
    return user, space, document


def test_sql_queue_claims_and_marks_completion(db_session):
    user, space, document = _seed_user_space_document(db_session)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="parsing",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.commit()

    queue = SqlDocumentProcessingQueue()
    payload = queue.claim_next_job()
    assert payload is not None
    assert payload.document_id == document.id

    queue.mark_job_completed(job.id)
    db_session.expire_all()
    refreshed = db_session.get(DocumentProcessingJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.completed_at is not None


def test_worker_marks_document_failed_when_blob_is_missing(db_session):
    user, space, document = _seed_user_space_document(db_session)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="parsing",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.commit()

    queue = InMemoryDocumentProcessingQueue()
    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=space.id,
            uploaded_by=user.id,
            requested_stage="parsing",
            attempt=1,
        )
    )
    assert drain_document_jobs(queue=queue, storage=InMemoryDocumentStorage()) == 1
    db_session.expire_all()
    refreshed_document = db_session.get(Document, document.id)
    refreshed_job = db_session.get(DocumentProcessingJob, job.id)
    assert refreshed_document is not None
    assert refreshed_document.processing_status["overall"] == "failed"
    assert refreshed_job is not None
    assert refreshed_job.status == "failed"


def test_worker_replaces_existing_chunks_idempotently(db_session):
    user, space, document = _seed_user_space_document(db_session)
    existing_chunk = DocumentChunk.from_text(
        document_id=document.id,
        space_id=space.id,
        chunk_index=0,
        text_content="stale chunk",
    )
    db_session.add(existing_chunk)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="parsing",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.commit()

    storage = InMemoryDocumentStorage()
    storage.store_original_file(document.storage_key, b"fresh content for parsing")
    queue = InMemoryDocumentProcessingQueue()
    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=space.id,
            uploaded_by=user.id,
            requested_stage="parsing",
            attempt=1,
        )
    )
    assert drain_document_jobs(queue=queue, storage=storage) == 1
    db_session.expire_all()
    chunks = db_session.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).all()
    assert len(chunks) == 1
    assert chunks[0].text_content == "fresh content for parsing"
