from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.modules.documents.api.schemas import DocumentUpdateRequest
from ragdoll.modules.documents.domain.policies import ensure_destination_space_accepts_documents
from ragdoll.modules.documents.infrastructure.repository import DocumentsRepository
from ragdoll.modules.ingestion.infrastructure.repository import IngestionRepository
from ragdoll.modules.spaces.infrastructure.repository import SpacesRepository
from ragdoll.platform.db.models import Document
from ragdoll.platform.graph import GraphCleanupService
from ragdoll.platform.storage import DocumentStorageService
from ragdoll.platform.vector import VectorCleanupService


def move_document(session: Session, subject: str, document: Document, payload: DocumentUpdateRequest) -> Document:
    owner_user_id = UUID(subject)
    destination_space = SpacesRepository(session).get_owned_or_404(owner_user_id, payload.space_id)
    ensure_destination_space_accepts_documents(destination_space)
    document.space_id = destination_space.id
    session.commit()
    session.refresh(document)
    return document


def delete_document(
    session: Session,
    document: Document,
    storage: DocumentStorageService,
    vector_cleanup: VectorCleanupService,
    graph_cleanup: GraphCleanupService,
) -> None:
    storage.delete_original_file(document.storage_key)
    storage.delete_derived_artifacts(document.id)
    vector_cleanup.cleanup_document(document.id)
    graph_cleanup.cleanup_document(document.id)
    IngestionRepository(session).clear_entities_for_document(document.id)
    IngestionRepository(session).prune_orphan_canonical_entities()
    DocumentsRepository(session).soft_delete(document)
    session.commit()
