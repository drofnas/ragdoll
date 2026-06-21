from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile

from ragdoll.api.dependencies import (
    CurrentUserDep,
    DatabaseSessionDep,
    DocumentProcessingQueueDep,
    DocumentStorageDep,
    GraphCleanupDep,
    SettingsDep,
    VectorCleanupDep,
)
from ragdoll.api.shared_schemas import ProblemResponse
from ragdoll.modules.ingestion.api.schemas import (
    BatchDocumentStatusRequest,
    BatchDocumentStatusResponse,
    DocumentProcessingStatusResponse,
    UploadDocumentResponse,
)
from ragdoll.modules.ingestion.application.commands import requeue_document_for_parsing, upload_document
from ragdoll.modules.ingestion.application.queries import get_batch_document_statuses, get_document_status

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

COMMON_RESPONSES = {
    400: {"model": ProblemResponse, "description": "Bad request."},
    401: {"model": ProblemResponse, "description": "Authentication required."},
    404: {"model": ProblemResponse, "description": "Requested document was not found."},
    409: {"model": ProblemResponse, "description": "Request conflicts with current document state."},
    413: {"model": ProblemResponse, "description": "Upload rejected by plan limits."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
    429: {"model": ProblemResponse, "description": "Upload rate limit exceeded."},
}


@router.post("/uploads", response_model=UploadDocumentResponse, status_code=201, responses=COMMON_RESPONSES)
async def create_upload(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    settings: SettingsDep,
    storage: DocumentStorageDep,
    queue: DocumentProcessingQueueDep,
    file: UploadFile = File(...),
    space_id: UUID | None = Query(default=None),
) -> UploadDocumentResponse:
    content = await file.read()
    return upload_document(
        db,
        current_user=current_user,
        settings=settings,
        storage=storage,
        queue=queue,
        filename=file.filename or "",
        content_type=file.content_type,
        content=content,
        space_id=space_id,
    )


@router.get(
    "/documents/{document_id}/status",
    response_model=DocumentProcessingStatusResponse,
    responses=COMMON_RESPONSES,
)
def read_document_status(
    document_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
) -> DocumentProcessingStatusResponse:
    return get_document_status(db, current_user.subject, document_id)


@router.post(
    "/documents/status/batch",
    response_model=BatchDocumentStatusResponse,
    responses=COMMON_RESPONSES,
)
def read_batch_document_status(
    payload: BatchDocumentStatusRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
) -> BatchDocumentStatusResponse:
    return get_batch_document_statuses(db, current_user.subject, payload.document_ids)


@router.post(
    "/documents/{document_id}/reprocess",
    response_model=DocumentProcessingStatusResponse,
    responses=COMMON_RESPONSES,
)
def reprocess_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    queue: DocumentProcessingQueueDep,
    storage: DocumentStorageDep,
    vector_cleanup: VectorCleanupDep,
    graph_cleanup: GraphCleanupDep,
) -> DocumentProcessingStatusResponse:
    get_document_status(db, current_user.subject, document_id)
    storage.delete_derived_artifacts(document_id)
    vector_cleanup.cleanup_document(document_id)
    graph_cleanup.cleanup_document(document_id)
    requeue_document_for_parsing(
        db,
        subject=current_user.subject,
        document_id=document_id,
        queue=queue,
        clear_existing_chunks=True,
    )
    return get_document_status(db, current_user.subject, document_id)


@router.post(
    "/documents/{document_id}/retry/parsing",
    response_model=DocumentProcessingStatusResponse,
    responses=COMMON_RESPONSES,
)
def retry_parsing(
    document_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    queue: DocumentProcessingQueueDep,
) -> DocumentProcessingStatusResponse:
    requeue_document_for_parsing(
        db,
        subject=current_user.subject,
        document_id=document_id,
        queue=queue,
        clear_existing_chunks=False,
    )
    return get_document_status(db, current_user.subject, document_id)
