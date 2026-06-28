from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Iterable, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ragdoll.core.config import get_settings
from ragdoll.modules.ingestion.domain.policies import mark_processing_stage_failed
from ragdoll.platform.db.models import DocumentProcessingJob
from ragdoll.platform.db.session import get_session_factory


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


PROCESSING_STAGES = ("parsing", "vector", "extraction", "graph")
EXTRACTION_STAGE = "extraction"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _resolve_processing_stage(job: DocumentProcessingJob) -> str:
    payload = job.document.processing_status or {}
    for stage in PROCESSING_STAGES:
        if payload.get(stage) == "processing":
            return stage
    if job.requested_stage in PROCESSING_STAGES:
        return job.requested_stage
    return "parsing"


def _timeout_seconds_for_stage(stage: str) -> float:
    settings = get_settings()
    if stage == EXTRACTION_STAGE:
        return settings.document_processing_timeout_seconds_extraction
    return settings.document_processing_timeout_seconds_default


def _stale_processing_detail(stage: str, timeout_seconds: float) -> str:
    minutes = int(timeout_seconds // 60) if timeout_seconds % 60 == 0 else round(timeout_seconds / 60, 1)
    return (
        f"Document processing timed out during {stage} after about {minutes} minutes. "
        "The worker or backend may have restarted, or processing may have been abandoned. "
        "You can refresh to reprocess the document."
    )


def reconcile_stale_processing_jobs(session: Session, *, document_ids: Iterable[UUID] | None = None) -> int:
    ids = tuple(dict.fromkeys(document_ids or ()))
    statement = select(DocumentProcessingJob).where(DocumentProcessingJob.status == "processing")
    if document_ids is not None:
        if not ids:
            return 0
        statement = statement.where(DocumentProcessingJob.document_id.in_(ids))

    now = utc_now()
    reconciled = 0
    for job in session.scalars(statement).all():
        reference_at = _as_utc(job.started_at or job.queued_at)
        stage = _resolve_processing_stage(job)
        timeout_seconds = _timeout_seconds_for_stage(stage)
        if (_as_utc(now) - reference_at).total_seconds() < timeout_seconds:
            continue
        detail = _stale_processing_detail(stage, timeout_seconds)
        job.status = "failed"
        job.completed_at = now
        job.visible_error_detail = detail[:2000]
        job.document.processing_status = mark_processing_stage_failed(
            job.document.processing_status,
            failed_stage=stage,
            detail=detail,
        )
        reconciled += 1

    if reconciled > 0:
        session.commit()
    return reconciled


@dataclass(frozen=True)
class ProcessingJobPayload:
    job_id: UUID
    document_id: UUID
    space_id: UUID
    uploaded_by: UUID
    requested_stage: str
    attempt: int
    job_kind: str = "upload"
    cleanup_derived_artifacts: bool = False
    reset_document_content: bool = False
    clear_existing_chunks: bool = False
    clear_existing_entities: bool = False
    cleanup_vectors: bool = False
    cleanup_graph: bool = False


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
            reconcile_stale_processing_jobs(session)
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
                job_kind=job.job_kind,
                cleanup_derived_artifacts=job.cleanup_derived_artifacts,
                reset_document_content=job.reset_document_content,
                clear_existing_chunks=job.clear_existing_chunks,
                clear_existing_entities=job.clear_existing_entities,
                cleanup_vectors=job.cleanup_vectors,
                cleanup_graph=job.cleanup_graph,
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
        session = get_session_factory()()
        try:
            reconcile_stale_processing_jobs(session)
        finally:
            session.close()
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
    if settings.e2e_shared_backends:
        return SqlDocumentProcessingQueue()
    if settings.e2e_memory_backends:
        return InMemoryDocumentProcessingQueue()
    return SqlDocumentProcessingQueue()
