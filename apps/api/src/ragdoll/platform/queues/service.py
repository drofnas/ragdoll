from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Protocol
from uuid import UUID

from sqlalchemy import select

from ragdoll.core.config import get_settings
from ragdoll.platform.db.models import DocumentProcessingJob
from ragdoll.platform.db.session import get_session_factory


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ProcessingJobPayload:
    job_id: UUID
    document_id: UUID
    space_id: UUID
    uploaded_by: UUID
    requested_stage: str
    attempt: int


class DocumentProcessingQueueService(Protocol):
    def enqueue(self, payload: ProcessingJobPayload) -> None: ...

    def claim_next_job(self) -> ProcessingJobPayload | None: ...

    def mark_job_completed(self, job_id: UUID) -> None: ...

    def mark_job_failed(self, job_id: UUID, detail: str) -> None: ...


class SqlDocumentProcessingQueue:
    """Database-backed queue that treats queued job rows as the source of truth."""

    def enqueue(self, payload: ProcessingJobPayload) -> None:
        del payload

    def claim_next_job(self) -> ProcessingJobPayload | None:
        session = get_session_factory()()
        try:
            job = session.scalar(
                select(DocumentProcessingJob)
                .where(DocumentProcessingJob.status == "queued")
                .order_by(DocumentProcessingJob.queued_at.asc())
                .limit(1)
            )
            if job is None:
                return None
            job.status = "processing"
            job.started_at = utc_now()
            job.visible_error_detail = None
            session.commit()
            return ProcessingJobPayload(
                job_id=job.id,
                document_id=job.document_id,
                space_id=job.space_id,
                uploaded_by=job.uploaded_by,
                requested_stage=job.requested_stage,
                attempt=job.attempt,
            )
        finally:
            session.close()

    def mark_job_completed(self, job_id: UUID) -> None:
        session = get_session_factory()()
        try:
            job = session.get(DocumentProcessingJob, job_id)
            if job is None:
                return
            job.status = "completed"
            job.completed_at = utc_now()
            job.visible_error_detail = None
            session.commit()
        finally:
            session.close()

    def mark_job_failed(self, job_id: UUID, detail: str) -> None:
        session = get_session_factory()()
        try:
            job = session.get(DocumentProcessingJob, job_id)
            if job is None:
                return
            job.status = "failed"
            job.completed_at = utc_now()
            job.visible_error_detail = detail[:2000]
            session.commit()
        finally:
            session.close()


class InMemoryDocumentProcessingQueue:
    """Test-focused queue that still mirrors state onto relational job rows."""

    def __init__(self) -> None:
        self._items: list[ProcessingJobPayload] = []

    def enqueue(self, payload: ProcessingJobPayload) -> None:
        self._items.append(payload)

    def claim_next_job(self) -> ProcessingJobPayload | None:
        if not self._items:
            return None
        payload = self._items.pop(0)
        session = get_session_factory()()
        try:
            job = session.get(DocumentProcessingJob, payload.job_id)
            if job is not None:
                job.status = "processing"
                job.started_at = utc_now()
                job.visible_error_detail = None
                session.commit()
        finally:
            session.close()
        return payload

    def mark_job_completed(self, job_id: UUID) -> None:
        SqlDocumentProcessingQueue().mark_job_completed(job_id)

    def mark_job_failed(self, job_id: UUID, detail: str) -> None:
        SqlDocumentProcessingQueue().mark_job_failed(job_id, detail)

    def queued_job_ids(self) -> list[UUID]:
        return [item.job_id for item in self._items]


@lru_cache(maxsize=1)
def get_document_processing_queue() -> DocumentProcessingQueueService:
    settings = get_settings()
    if settings.e2e_memory_backends:
        return InMemoryDocumentProcessingQueue()
    return SqlDocumentProcessingQueue()
