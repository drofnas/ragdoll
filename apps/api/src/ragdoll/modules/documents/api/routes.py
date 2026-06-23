from __future__ import annotations

from datetime import datetime
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Query, Response

from ragdoll.api.dependencies import (
    CurrentUserDep,
    DatabaseSessionDep,
    DocumentStorageDep,
    GraphCleanupDep,
    PaginationDep,
    SpaceScopeDep,
    VectorCleanupDep,
)
from ragdoll.api.shared_schemas import MutationResult, ProblemResponse
from ragdoll.modules.documents.api.schemas import DocumentDetail, DocumentListResponse, DocumentUpdateRequest
from ragdoll.modules.documents.application.commands import delete_document, move_document
from ragdoll.modules.documents.application.queries import (
    build_document_detail,
    get_document_detail,
    get_document_model,
    list_documents,
)
from ragdoll.modules.documents.domain.policies import raise_document_blob_missing

router = APIRouter(prefix="/documents", tags=["documents"])

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    404: {"model": ProblemResponse, "description": "Requested document was not found."},
    409: {"model": ProblemResponse, "description": "Document metadata exists but backing storage is unavailable."},
    503: {"model": ProblemResponse, "description": "Document storage is temporarily unavailable."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


def _attachment_content_disposition(filename: str) -> str:
    basename = (filename or "document").strip() or "document"
    basename = basename.replace("\r", "").replace("\n", "").replace('"', "'")[:200]
    ascii_name = "".join(char if char.isalnum() or char in "._-" else "_" for char in basename) or "document"
    encoded = quote(basename, safe="")
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded}'


@router.get("", response_model=DocumentListResponse, responses=COMMON_RESPONSES)
def read_documents(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    pagination: PaginationDep,
    space_scope: SpaceScopeDep,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    file_type: str | None = Query(default=None),
    uploaded_by: str | None = Query(default=None),
) -> DocumentListResponse:
    return list_documents(
        db,
        current_user.subject,
        pagination,
        space_scope=space_scope,
        date_from=date_from,
        date_to=date_to,
        file_type=file_type,
        uploaded_by=uploaded_by,
    )


@router.get("/{document_id}", response_model=DocumentDetail, responses=COMMON_RESPONSES)
def read_document(document_id: UUID, current_user: CurrentUserDep, db: DatabaseSessionDep) -> DocumentDetail:
    return get_document_detail(db, current_user.subject, document_id)


@router.patch("/{document_id}", response_model=DocumentDetail, responses=COMMON_RESPONSES)
def patch_document(
    document_id: UUID,
    payload: DocumentUpdateRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
) -> DocumentDetail:
    document = get_document_model(db, current_user.subject, document_id)
    updated_document = move_document(db, current_user.subject, document, payload)
    return build_document_detail(updated_document)


@router.delete("/{document_id}", response_model=MutationResult, responses=COMMON_RESPONSES)
def delete_document_route(
    document_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    storage: DocumentStorageDep,
    vector_cleanup: VectorCleanupDep,
    graph_cleanup: GraphCleanupDep,
) -> MutationResult:
    document = get_document_model(db, current_user.subject, document_id)
    delete_document(db, document, storage, vector_cleanup, graph_cleanup)
    return MutationResult(message="Document deleted successfully.")


@router.get("/{document_id}/download", responses=COMMON_RESPONSES)
def download_document(
    document_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    storage: DocumentStorageDep,
) -> Response:
    document = get_document_model(db, current_user.subject, document_id)
    try:
        body = storage.download_original_file(document.storage_key)
    except FileNotFoundError:
        raise_document_blob_missing()
    return Response(
        content=body,
        media_type=document.mime_type,
        headers={"Content-Disposition": _attachment_content_disposition(document.original_filename)},
    )
