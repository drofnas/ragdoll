from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
import os
import socket
import time
from typing import Any, Iterable, Protocol
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import ConfigurationError, QueueUnavailableError
from ragdoll.core.logging import get_logger
from ragdoll.modules.ingestion.domain.policies import mark_processing_stage_failed
from ragdoll.platform.db.models import DocumentProcessingJob
from ragdoll.platform.db.session import get_session_factory

logger = get_logger("ragdoll.platform.queues")


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


def _payload_from_job(job: DocumentProcessingJob) -> ProcessingJobPayload:
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
            return _payload_from_job(job)
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


def _decode_redis_value(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _redis_dependency_module() -> Any:
    try:
        import redis
    except ModuleNotFoundError as exc:
        raise ConfigurationError("Redis queue backend requires the 'redis' Python package.") from exc
    return redis


def _build_redis_client(settings: Settings) -> Any:
    redis_url = (settings.redis_url or "").strip()
    if not redis_url:
        raise ConfigurationError("Redis queue backend requires REDIS_URL.")
    redis_module = _redis_dependency_module()
    return redis_module.Redis.from_url(
        redis_url,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=max(settings.document_vector_block_timeout_seconds + 1, 5),
    )


def _is_busy_group_error(exc: Exception) -> bool:
    return "BUSYGROUP" in str(exc).upper()


def ping_redis_queue(settings: Settings | None = None, *, client: Any | None = None) -> None:
    """Verify the configured Redis queue backend accepts commands."""
    active_settings = settings or get_settings()
    active_client = client or _build_redis_client(active_settings)
    try:
        active_client.ping()
    except Exception as exc:
        raise QueueUnavailableError("Redis queue backend is not reachable.") from exc


class RedisDocumentProcessingQueue:
    """Redis Streams transport with SQL rows as the durable processing ledger."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
        monotonic_fn: Any = time.monotonic,
        consumer_name: str | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or _build_redis_client(self._settings)
        self._stream = self._settings.document_vector_queue_stream
        self._group = self._settings.document_vector_consumer_group
        self._consumer = (
            consumer_name
            or (self._settings.document_vector_consumer_name or "").strip()
            or f"{socket.gethostname()}-{os.getpid()}"
        )
        self._monotonic_fn = monotonic_fn
        self._group_ready = False
        self._last_repair_at = 0.0
        self._active_message_ids: dict[UUID, str] = {}

    def enqueue(self, payload: ProcessingJobPayload) -> None:
        self._ensure_consumer_group()
        self._xadd_job(payload.job_id)

    def claim_next_job(self) -> ProcessingJobPayload | None:
        self._ensure_consumer_group()
        self._repair_queued_jobs_if_due()

        for message_id, fields in self._read_new_messages():
            payload = self._claim_message(message_id, fields)
            if payload is not None:
                return payload

        for message_id, fields in self._claim_stale_pending_messages():
            payload = self._claim_message(message_id, fields)
            if payload is not None:
                return payload

        return None

    def mark_job_completed(self, job_id: UUID) -> None:
        SqlDocumentProcessingQueue().mark_job_completed(job_id)
        self._ack_active_message(job_id)

    def mark_job_failed(self, job_id: UUID, detail: str) -> None:
        SqlDocumentProcessingQueue().mark_job_failed(job_id, detail)
        self._ack_active_message(job_id)

    def _ensure_consumer_group(self) -> None:
        if self._group_ready:
            return
        try:
            self._client.xgroup_create(self._stream, self._group, id="0", mkstream=True)
        except Exception as exc:
            if not _is_busy_group_error(exc):
                raise QueueUnavailableError("Redis queue consumer group could not be created.") from exc
        self._group_ready = True

    def _xadd_job(self, job_id: UUID) -> None:
        try:
            self._client.xadd(
                self._stream,
                {"job_id": str(job_id)},
                maxlen=self._settings.document_vector_stream_maxlen,
                approximate=True,
            )
        except Exception as exc:
            raise QueueUnavailableError("Redis queue enqueue failed.") from exc

    def _read_new_messages(self) -> list[tuple[str, dict[str, object]]]:
        block_ms = int(self._settings.document_vector_block_timeout_seconds * 1000)
        try:
            response = self._client.xreadgroup(
                self._group,
                self._consumer,
                {self._stream: ">"},
                count=10,
                block=block_ms,
            )
        except Exception as exc:
            raise QueueUnavailableError("Redis queue read failed.") from exc
        return self._stream_messages(response)

    def _claim_stale_pending_messages(self) -> list[tuple[str, dict[str, object]]]:
        if not hasattr(self._client, "xautoclaim"):
            return []
        min_idle_ms = int(self._settings.document_processing_timeout_seconds_default * 1000)
        try:
            response = self._client.xautoclaim(
                self._stream,
                self._group,
                self._consumer,
                min_idle_time=min_idle_ms,
                start_id="0-0",
                count=10,
            )
        except Exception as exc:
            raise QueueUnavailableError("Redis queue pending-claim failed.") from exc

        messages: object
        if isinstance(response, tuple) and len(response) >= 2:
            messages = response[1]
        else:
            messages = response
        return [
            (_decode_redis_value(message_id), dict(fields))
            for message_id, fields in messages or []
        ]

    def _stream_messages(self, response: object) -> list[tuple[str, dict[str, object]]]:
        messages: list[tuple[str, dict[str, object]]] = []
        for _stream_name, stream_messages in response or []:
            for message_id, fields in stream_messages:
                messages.append((_decode_redis_value(message_id), dict(fields)))
        return messages

    def _claim_message(self, message_id: str, fields: dict[str, object]) -> ProcessingJobPayload | None:
        job_id_raw = fields.get("job_id") or fields.get(b"job_id")
        try:
            job_id = UUID(_decode_redis_value(job_id_raw))
        except (TypeError, ValueError):
            self._ack_message(message_id)
            return None

        payload = self._claim_sql_job(job_id)
        if payload is None:
            self._ack_message(message_id)
            return None

        self._active_message_ids[payload.job_id] = message_id
        return payload

    def _claim_sql_job(self, job_id: UUID) -> ProcessingJobPayload | None:
        session = get_session_factory()()
        try:
            reconcile_stale_processing_jobs(session)
            now = utc_now()
            result = session.execute(
                update(DocumentProcessingJob)
                .where(
                    DocumentProcessingJob.id == job_id,
                    DocumentProcessingJob.status == "queued",
                )
                .values(
                    status="processing",
                    started_at=now,
                    visible_error_detail=None,
                )
            )
            if result.rowcount != 1:
                session.rollback()
                return None
            job = session.get(DocumentProcessingJob, job_id)
            if job is None:
                session.rollback()
                return None
            payload = _payload_from_job(job)
            session.commit()
            return payload
        finally:
            session.close()

    def _repair_queued_jobs_if_due(self) -> None:
        interval_seconds = self._settings.document_vector_repair_interval_seconds
        now = self._monotonic_fn()
        if interval_seconds > 0 and now - self._last_repair_at < interval_seconds:
            return
        self._last_repair_at = now

        session = get_session_factory()()
        try:
            reconcile_stale_processing_jobs(session)
            job_ids = list(
                session.scalars(
                    select(DocumentProcessingJob.id)
                    .where(DocumentProcessingJob.status == "queued")
                    .order_by(DocumentProcessingJob.queued_at.asc())
                    .limit(100)
                )
            )
        finally:
            session.close()

        for job_id in job_ids:
            self._xadd_job(job_id)

    def _ack_active_message(self, job_id: UUID) -> None:
        message_id = self._active_message_ids.pop(job_id, None)
        if message_id is not None:
            self._ack_message(message_id)

    def _ack_message(self, message_id: str) -> None:
        try:
            self._client.xack(self._stream, self._group, message_id)
        except Exception:
            logger.warning(
                "Redis queue ack failed stream=%s group=%s message_id=%s",
                self._stream,
                self._group,
                message_id,
                exc_info=True,
            )


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
    if settings.e2e_memory_backends:
        return InMemoryDocumentProcessingQueue()
    if settings.document_processing_queue_backend == "memory":
        return InMemoryDocumentProcessingQueue()
    if settings.document_processing_queue_backend == "redis":
        return RedisDocumentProcessingQueue(settings=settings)
    return SqlDocumentProcessingQueue()
