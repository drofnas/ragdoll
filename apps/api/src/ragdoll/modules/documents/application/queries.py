from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.core.pagination import PaginationParams
from ragdoll.modules.documents.api.schemas import DocumentDetail, DocumentListItem, DocumentListResponse
from ragdoll.modules.documents.domain.policies import (
    normalize_optional_file_type,
    normalize_processing_status,
    normalize_uploaded_by_filter,
    validate_date_range,
)
from ragdoll.modules.documents.infrastructure.repository import DocumentListFilters, DocumentsRepository
from ragdoll.modules.spaces.infrastructure.repository import SpacesRepository
from ragdoll.platform.db.models import Document


def build_document_list_item(document: Document) -> DocumentListItem:
    return DocumentListItem(
        id=document.id,
        space_id=document.space_id,
        uploaded_by=document.uploaded_by,
        title=document.title,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        file_type=document.file_type,
        file_size=document.file_size,
        source_kind=document.source_kind,
        source_label=document.source_label,
        processing_status=normalize_processing_status(document.processing_status),
        chunk_count=document.chunk_count,
        indexed_chunk_count=document.indexed_chunk_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


def build_document_detail(document: Document) -> DocumentDetail:
    return DocumentDetail(
        **build_document_list_item(document).model_dump(),
        preview_text=document.preview_text,
        original_text_content=document.original_text_content,
    )


def _owner_user_id(subject: str) -> UUID:
    return UUID(subject)


def list_documents(
    session: Session,
    subject: str,
    pagination: PaginationParams,
    *,
    space_scope: SpaceScope,
    date_from: datetime | None,
    date_to: datetime | None,
    file_type: str | None,
    uploaded_by: str | None,
) -> DocumentListResponse:
    owner_user_id = _owner_user_id(subject)
    validate_date_range(date_from, date_to)
    if space_scope.space_id is not None:
        SpacesRepository(session).get_owned_or_404(owner_user_id, space_scope.space_id)
    repo = DocumentsRepository(session)
    items, total = repo.list_visible(
        owner_user_id,
        pagination,
        filters=DocumentListFilters(
            date_from=date_from,
            date_to=date_to,
            file_type=normalize_optional_file_type(file_type),
            uploaded_by=normalize_uploaded_by_filter(uploaded_by, current_user_id=owner_user_id),
        ),
        space_id=space_scope.space_id,
    )
    return DocumentListResponse(
        items=[build_document_list_item(item) for item in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_document_model(session: Session, subject: str, document_id: UUID) -> Document:
    return DocumentsRepository(session).get_visible_or_404(_owner_user_id(subject), document_id)


def get_document_detail(session: Session, subject: str, document_id: UUID) -> DocumentDetail:
    return build_document_detail(get_document_model(session, subject, document_id))
