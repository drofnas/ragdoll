from __future__ import annotations

from ragdoll.modules.ingestion.application.service import process_job_payload
from ragdoll.platform.graph import GraphCleanupService
from ragdoll.platform.llm import EmbeddingGenerationService, EntityExtractionService
from ragdoll.platform.queues import DocumentProcessingQueueService, get_document_processing_queue
from ragdoll.platform.storage import DocumentStorageService
from ragdoll.platform.vector import VectorCleanupService


def process_next_document_job(
    queue: DocumentProcessingQueueService | None = None,
    *,
    storage: DocumentStorageService | None = None,
    embedding_service: EmbeddingGenerationService | None = None,
    entity_extraction_service: EntityExtractionService | None = None,
    vector_cleanup: VectorCleanupService | None = None,
    graph_cleanup: GraphCleanupService | None = None,
) -> bool:
    """Claim and execute one queued document-processing job."""
    active_queue = queue or get_document_processing_queue()
    payload = active_queue.claim_next_job()
    if payload is None:
        return False
    process_job_payload(
        payload,
        active_queue,
        storage=storage,
        embedding_service=embedding_service,
        entity_extraction_service=entity_extraction_service,
        vector_cleanup=vector_cleanup,
        graph_cleanup=graph_cleanup,
    )
    return True


def drain_document_jobs(
    *,
    max_jobs: int | None = None,
    queue: DocumentProcessingQueueService | None = None,
    storage: DocumentStorageService | None = None,
    embedding_service: EmbeddingGenerationService | None = None,
    entity_extraction_service: EntityExtractionService | None = None,
    vector_cleanup: VectorCleanupService | None = None,
    graph_cleanup: GraphCleanupService | None = None,
) -> int:
    """Process queued jobs until the queue is empty or the limit is reached."""
    processed = 0
    active_queue = queue or get_document_processing_queue()
    while max_jobs is None or processed < max_jobs:
        if not process_next_document_job(
            active_queue,
            storage=storage,
            embedding_service=embedding_service,
            entity_extraction_service=entity_extraction_service,
            vector_cleanup=vector_cleanup,
            graph_cleanup=graph_cleanup,
        ):
            break
        processed += 1
    return processed
