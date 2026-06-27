from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ragdoll.api.shared_schemas import ProcessingStatus


class DocumentProcessingJobResponse(BaseModel):
    id: UUID
    requested_stage: str
    status: str
    attempt: int = Field(ge=1)
    visible_error_detail: str | None = None
    queued_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class DocumentQueueRuntimeResponse(BaseModel):
    job_id: UUID
    queue_job_id: str
    queue_name: str
    status: str
    stage: str | None = None
    detail: str | None = None
    worker_name: str | None = None
    queue_position: int | None = Field(default=None, ge=1)
    chunk_progress_current: int = Field(default=0, ge=0)
    chunk_progress_total: int = Field(default=0, ge=0)
    enqueued_at: datetime | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UploadDocumentResponse(BaseModel):
    document_id: UUID
    job_id: UUID
    filename: str
    processing_status: ProcessingStatus


class DocumentProcessingStatusResponse(BaseModel):
    document_id: UUID
    space_id: UUID
    uploaded_by: UUID
    processing_status: ProcessingStatus
    chunk_count: int = Field(ge=0)
    indexed_chunk_count: int = Field(ge=0)
    latest_job: DocumentProcessingJobResponse | None = None
    active_job: DocumentProcessingJobResponse | None = None
    queue_runtime: DocumentQueueRuntimeResponse | None = None
    queued_job_count: int = Field(default=0, ge=0)
    has_queued_reprocess: bool = False
    updated_at: datetime


class BatchDocumentStatusRequest(BaseModel):
    document_ids: list[UUID] = Field(default_factory=list, max_length=100)


class BatchDocumentStatusResponse(BaseModel):
    statuses: list[DocumentProcessingStatusResponse]
