from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Iterable, Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import ConfigurationError, QueueUnavailableError
from ragdoll.modules.ingestion.domain.policies import mark_processing_stage_failed
from ragdoll.platform.db.models import DocumentProcessingJob
from ragdoll.platform.db.session import get_session_factory


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


PROCESSING_STAGES = ("parsing", "vector", "extraction", "graph")
EXTRACTION_STAGE = "extraction"


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
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
        assert reference_at is not None
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


@dataclass(frozen=True)
class DocumentQueueRuntime:
    job_id: UUID
    queue_job_id: str
    queue_name: str
    status: str
    stage: str | None = None
    detail: str | None = None
    worker_name: str | None = None
    queue_position: int | None = None
    chunk_progress_current: int = 0
    chunk_progress_total: int = 0
    enqueued_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentProcessingQueueService(Protocol):
    def enqueue(self, payload: ProcessingJobPayload) -> None: ...

    def mark_job_completed(self, job_id: UUID) -> None: ...

    def mark_job_failed(self, job_id: UUID, detail: str) -> None: ...

    def read_runtime(self, job_id: UUID) -> DocumentQueueRuntime | None: ...


def _redis_dependency_module() -> Any:
    try:
        import redis
    except ModuleNotFoundError as exc:
        raise ConfigurationError("Redis queue backend requires the 'redis' Python package.") from exc
    return redis


def _rq_dependencies() -> tuple[Any, Any, Any]:
    try:
        from rq import Queue
        from rq.exceptions import NoSuchJobError
        from rq.job import Job
    except ModuleNotFoundError as exc:
        raise ConfigurationError("RQ worker runtime requires the 'rq' Python package.") from exc
    return Queue, Job, NoSuchJobError


def _build_redis_client(settings: Settings) -> Any:
    redis_url = (settings.redis_url or "").strip()
    if not redis_url:
        raise ConfigurationError("Redis queue backend requires REDIS_URL.")
    redis_module = _redis_dependency_module()
    return redis_module.Redis.from_url(
        redis_url,
        decode_responses=False,
        socket_connect_timeout=5,
        socket_timeout=5,
    )


def _coerce_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8").strip()
        except UnicodeDecodeError:
            return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return str(value).strip() or None


def ping_redis_queue(settings: Settings | None = None, *, client: Any | None = None) -> None:
    active_settings = settings or get_settings()
    active_client = client or _build_redis_client(active_settings)
    try:
        active_client.ping()
    except Exception as exc:
        raise QueueUnavailableError("Redis queue backend is not reachable.") from exc


def _mark_sql_job_completed(job_id: UUID) -> None:
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


def _mark_sql_job_failed(job_id: UUID, detail: str) -> None:
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


def _coerce_int(value: object, *, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, bytes):
        try:
            return int(value.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def _coerce_datetime(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return None
    if isinstance(value, str):
        try:
            return _as_utc(datetime.fromisoformat(value))
        except ValueError:
            return None
    return None


class RedisDocumentProcessingQueue:
    """RQ-backed document-processing queue with SQL rows as the durable status ledger."""

    def __init__(
        self,
        *,
        settings: Settings | None = None,
        client: Any | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._client = client or _build_redis_client(self._settings)

    @property
    def queue_name(self) -> str:
        return self._settings.document_processing_queue_name

    def enqueue(self, payload: ProcessingJobPayload) -> None:
        Queue, _, _ = _rq_dependencies()
        from ragdoll.workers.document_pipeline import run_document_processing_job

        queue = Queue(self.queue_name, connection=self._client)
        try:
            job = queue.enqueue(
                run_document_processing_job,
                payload,
                job_id=str(payload.job_id),
                job_timeout=max(
                    int(self._settings.document_processing_job_timeout_seconds),
                    int(self._settings.document_processing_timeout_seconds_extraction),
                ),
                result_ttl=int(self._settings.document_processing_result_ttl_seconds),
                failure_ttl=int(self._settings.document_processing_failure_ttl_seconds),
                description=f"document:{payload.document_id}:{payload.requested_stage}",
            )
            job.meta.update(
                {
                    "stage": payload.requested_stage,
                    "detail": None,
                    "chunk_progress_current": 0,
                    "chunk_progress_total": 0,
                    "updated_at": utc_now().isoformat(),
                }
            )
            job.save_meta()
        except Exception as exc:
            raise QueueUnavailableError("RQ enqueue failed.") from exc

    def mark_job_completed(self, job_id: UUID) -> None:
        _mark_sql_job_completed(job_id)

    def mark_job_failed(self, job_id: UUID, detail: str) -> None:
        _mark_sql_job_failed(job_id, detail)

    def read_runtime(self, job_id: UUID) -> DocumentQueueRuntime | None:
        Queue, Job, NoSuchJobError = _rq_dependencies()
        try:
            job = Job.fetch(str(job_id), connection=self._client)
        except NoSuchJobError:
            return None
        except Exception as exc:
            raise QueueUnavailableError("RQ runtime lookup failed.") from exc

        try:
            status = str(job.get_status(refresh=True))
            queue_name = _coerce_text(getattr(job, "origin", None)) or self.queue_name
            queue = Queue(queue_name, connection=self._client)
            queue_position: int | None = None
            if status == "queued":
                job_ids = [_coerce_text(value) for value in queue.job_ids]
                try:
                    queue_position = job_ids.index(str(job.id)) + 1
                except ValueError:
                    queue_position = None
            meta = dict(job.meta or {})
            return DocumentQueueRuntime(
                job_id=job_id,
                queue_job_id=str(job.id),
                queue_name=queue_name,
                status=status,
                stage=_coerce_text(meta.get("stage")),
                detail=_coerce_text(meta.get("detail")),
                worker_name=_coerce_text(getattr(job, "worker_name", None)),
                queue_position=queue_position,
                chunk_progress_current=_coerce_int(meta.get("chunk_progress_current")),
                chunk_progress_total=_coerce_int(meta.get("chunk_progress_total")),
                enqueued_at=_as_utc(getattr(job, "enqueued_at", None) or getattr(job, "created_at", None)),
                started_at=_as_utc(getattr(job, "started_at", None)),
                ended_at=_as_utc(getattr(job, "ended_at", None)),
                updated_at=_coerce_datetime(meta.get("updated_at"))
                or _as_utc(getattr(job, "last_heartbeat", None))
                or _as_utc(getattr(job, "ended_at", None))
                or _as_utc(getattr(job, "started_at", None))
                or _as_utc(getattr(job, "enqueued_at", None)),
            )
        except Exception as exc:
            raise QueueUnavailableError("RQ runtime payload could not be read.") from exc


@lru_cache(maxsize=1)
def get_document_processing_queue() -> DocumentProcessingQueueService:
    return RedisDocumentProcessingQueue(settings=get_settings())
