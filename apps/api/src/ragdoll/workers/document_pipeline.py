from __future__ import annotations

from ragdoll.modules.ingestion.application.service import process_job_payload
from ragdoll.platform.queues import DocumentProcessingQueueService, get_document_processing_queue
from ragdoll.platform.storage import DocumentStorageService


def process_next_document_job(
    queue: DocumentProcessingQueueService | None = None,
    *,
    storage: DocumentStorageService | None = None,
) -> bool:
    """Claim and execute one queued document-processing job."""
    active_queue = queue or get_document_processing_queue()
    payload = active_queue.claim_next_job()
    if payload is None:
        return False
    process_job_payload(payload, active_queue, storage=storage)
    return True


def drain_document_jobs(
    *,
    max_jobs: int | None = None,
    queue: DocumentProcessingQueueService | None = None,
    storage: DocumentStorageService | None = None,
) -> int:
    """Process queued jobs until the queue is empty or the limit is reached."""
    processed = 0
    active_queue = queue or get_document_processing_queue()
    while max_jobs is None or processed < max_jobs:
        if not process_next_document_job(active_queue, storage=storage):
            break
        processed += 1
    return processed
