from __future__ import annotations

from typing import Any

from ragdoll.modules.ingestion.application.service import process_job_payload
from ragdoll.platform.graph import GraphCleanupService
from ragdoll.platform.llm import EmbeddingGenerationService, EntityExtractionService
from ragdoll.platform.queues import ProcessingJobPayload
from ragdoll.platform.storage import DocumentStorageService
from ragdoll.platform.vector import VectorCleanupService


def run_document_processing_job(
    payload: ProcessingJobPayload,
    *,
    storage: DocumentStorageService | None = None,
    embedding_service: EmbeddingGenerationService | None = None,
    entity_extraction_service: EntityExtractionService | None = None,
    vector_cleanup: VectorCleanupService | None = None,
    graph_cleanup: GraphCleanupService | None = None,
    current_job: Any | None = None,
) -> None:
    """Execute one document-processing job, typically inside an RQ worker."""
    active_job = current_job
    if active_job is None:
        try:
            from rq import get_current_job
        except ModuleNotFoundError:
            active_job = None
        else:
            active_job = get_current_job()

    process_job_payload(
        payload,
        storage=storage,
        embedding_service=embedding_service,
        entity_extraction_service=entity_extraction_service,
        vector_cleanup=vector_cleanup,
        graph_cleanup=graph_cleanup,
        current_job=active_job,
    )
