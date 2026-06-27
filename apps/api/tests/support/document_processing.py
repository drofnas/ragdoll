from __future__ import annotations

from typing import Any
from uuid import UUID

from ragdoll.platform.db.models import DocumentProcessingJob
from ragdoll.platform.db.session import get_session_factory
from ragdoll.platform.graph import GraphCleanupService
from ragdoll.platform.llm import EmbeddingGenerationService, EntityExtractionService
from ragdoll.platform.queues import (
    DocumentProcessingQueueService,
    DocumentQueueRuntime,
    ProcessingJobPayload,
    reconcile_stale_processing_jobs,
    utc_now,
)
from ragdoll.platform.storage import DocumentStorageService
from ragdoll.platform.vector import VectorCleanupService
from ragdoll.workers.document_pipeline import run_document_processing_job


class FakeDocumentProcessingQueue(DocumentProcessingQueueService):
    def __init__(self) -> None:
        self._items: list[ProcessingJobPayload] = []

    def enqueue(self, payload: ProcessingJobPayload) -> None:
        self._items.append(payload)

    def mark_job_completed(self, job_id: UUID) -> None:
        del job_id

    def mark_job_failed(self, job_id: UUID, detail: str) -> None:
        del job_id, detail

    def read_runtime(self, job_id: UUID) -> DocumentQueueRuntime | None:
        del job_id
        return None

    def queued_job_ids(self) -> list[UUID]:
        return [item.job_id for item in self._items]

    def claim_next_job(self) -> ProcessingJobPayload | None:
        payload = self.pop_next_payload()
        if payload is None:
            return None
        session = get_session_factory()()
        try:
            reconcile_stale_processing_jobs(session)
            job = session.get(DocumentProcessingJob, payload.job_id)
            if job is not None:
                job.status = "processing"
                job.started_at = utc_now()
                job.completed_at = None
                job.visible_error_detail = None
                session.commit()
        finally:
            session.close()
        return payload

    def pop_next_payload(self) -> ProcessingJobPayload | None:
        if not self._items:
            return None
        return self._items.pop(0)


def drain_test_document_jobs(
    queue: FakeDocumentProcessingQueue,
    *,
    max_jobs: int | None = None,
    storage: DocumentStorageService | None = None,
    embedding_service: EmbeddingGenerationService | None = None,
    entity_extraction_service: EntityExtractionService | None = None,
    vector_cleanup: VectorCleanupService | None = None,
    graph_cleanup: GraphCleanupService | None = None,
    current_job: Any | None = None,
) -> int:
    processed = 0
    while max_jobs is None or processed < max_jobs:
        payload = queue.pop_next_payload()
        if payload is None:
            break
        run_document_processing_job(
            payload,
            storage=storage,
            embedding_service=embedding_service,
            entity_extraction_service=entity_extraction_service,
            vector_cleanup=vector_cleanup,
            graph_cleanup=graph_cleanup,
            current_job=current_job,
        )
        processed += 1
    return processed
