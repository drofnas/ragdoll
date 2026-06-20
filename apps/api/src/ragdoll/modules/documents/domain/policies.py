from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from ragdoll.api.shared_schemas import ProcessingStatus
from ragdoll.core.exceptions import ApplicationError
from ragdoll.platform.db.models import Space

DOCUMENT_SOURCE_KIND_MANUAL_UPLOAD = "manual_upload"
DOCUMENT_SOURCE_KIND_EXTERNAL_SYNC = "external_sync"
DOCUMENT_BLOB_MISSING_TYPE = "https://ragdoll.dev/problems/document-blob-missing"


def normalize_processing_status(payload: dict[str, Any] | None) -> ProcessingStatus:
    return ProcessingStatus.model_validate(payload or {})


def validate_date_range(date_from: datetime | None, date_to: datetime | None) -> None:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise ApplicationError(
            "date_from must be before or equal to date_to.",
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        )


def normalize_optional_file_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    return normalized or None


def normalize_uploaded_by_filter(value: str | None, *, current_user_id: UUID) -> UUID | None:
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        raise ApplicationError(
            'uploaded_by must be "me" or a valid user UUID.',
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        )
    if normalized.lower() == "me":
        return current_user_id
    try:
        return UUID(normalized)
    except ValueError as exc:
        raise ApplicationError(
            'uploaded_by must be "me" or a valid user UUID.',
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        ) from exc


def ensure_destination_space_accepts_documents(space: Space) -> None:
    if space.archived_at is not None:
        raise ApplicationError(
            "Documents cannot be moved into an archived space.",
            status_code=409,
            title="Conflict",
            type_uri="https://ragdoll.dev/problems/document-destination-space-archived",
            code="document_destination_space_archived",
        )


def raise_document_blob_missing() -> None:
    raise ApplicationError(
        "The original document file is no longer available in object storage.",
        status_code=409,
        title="Conflict",
        type_uri=DOCUMENT_BLOB_MISSING_TYPE,
        code="document_blob_missing",
    )
