from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import urlencode

from ragdoll.api import dependencies as dependency_module
from ragdoll.platform.db.models import (
    CanonicalEntity,
    Document,
    DocumentChunk,
    DocumentChunkVector,
    Entity,
    GraphEdge,
    GraphNode,
    Space,
    User,
)
from ragdoll.platform.db.models.documents import default_processing_status_payload
from ragdoll.platform.graph import InMemoryGraphCleanupService
from ragdoll.platform.llm import DeterministicEmbeddingService, DeterministicEntityExtractionService, normalize_entity_name
from ragdoll.platform.queues import InMemoryDocumentProcessingQueue
from ragdoll.platform.storage import InMemoryDocumentStorage
from ragdoll.platform.vector import InMemoryVectorCleanupService


def register_and_login(api_client, *, email: str = "user@example.com", password: str = "testpass123") -> str:
    register = api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert register.status_code == 201, register.text
    login = api_client.post(
        "/api/v1/auth/login",
        content=urlencode({"username": email, "password": password}),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def default_space(db_session, user: User) -> Space:
    return (
        db_session.query(Space)
        .filter(Space.owner_user_id == user.id, Space.is_default.is_(True))
        .one()
    )


def completed_processing_status() -> dict[str, str | None]:
    payload = default_processing_status_payload()
    payload["overall"] = "completed"
    payload["parsing"] = "completed"
    payload["vector"] = "completed"
    payload["extraction"] = "completed"
    payload["graph"] = "completed"
    payload["detail"] = None
    return payload


def seed_retrieval_document(
    db_session,
    *,
    space: Space,
    uploader: User,
    title: str,
    text: str,
    file_type: str = "txt",
    mime_type: str = "text/plain",
    entity_specs: list[tuple[str, str]] | None = None,
    start_line: int = 1,
    chunks: list[tuple[str, int]] | None = None,
):
    chunk_specs = chunks or [(text, start_line)]
    document = Document(
        space_id=space.id,
        uploaded_by=uploader.id,
        title=title,
        original_filename=title,
        mime_type=mime_type,
        file_type=file_type,
        file_size=len(text.encode("utf-8")),
        storage_key=f"documents/{space.id}/{title}",
        source_kind="manual_upload",
        preview_text=text[:280],
        original_text_content=text,
        processing_status=completed_processing_status(),
        chunk_count=len(chunk_specs),
        indexed_chunk_count=len(chunk_specs),
        deleted_at=None,
    )
    db_session.add(document)
    db_session.flush()

    chunks_by_index: list[DocumentChunk] = []
    for chunk_index, (chunk_text, chunk_start_line) in enumerate(chunk_specs):
        chunk = DocumentChunk.from_text(
            document_id=document.id,
            space_id=space.id,
            chunk_index=chunk_index,
            start_line=chunk_start_line,
            text_content=chunk_text,
        )
        db_session.add(chunk)
        chunks_by_index.append(chunk)

        embedding = DeterministicEmbeddingService().generate_embeddings([chunk.text_content])[0]
        db_session.add(
            DocumentChunkVector(
                chunk_id=chunk.id,
                document_id=document.id,
                space_id=space.id,
                chunk_index=chunk.chunk_index,
                checksum=chunk.checksum,
                embedding_model="deterministic",
                embedding_dimensions=len(embedding),
                embedding=embedding,
            )
        )

    canonical_entities: list[CanonicalEntity] = []
    entity_chunk = chunks_by_index[0]
    for display_name, entity_type in entity_specs or []:
        normalized_name = normalize_entity_name(display_name)
        canonical = (
            db_session.query(CanonicalEntity)
            .filter(
                CanonicalEntity.space_id == space.id,
                CanonicalEntity.entity_type == entity_type,
                CanonicalEntity.normalized_name == normalized_name,
            )
            .one_or_none()
        )
        if canonical is None:
            canonical = CanonicalEntity(
                space_id=space.id,
                entity_type=entity_type,
                normalized_name=normalized_name,
                display_name=display_name,
            )
            db_session.add(canonical)
            db_session.flush()
        canonical_entities.append(canonical)
        db_session.add(
            Entity(
                space_id=space.id,
                document_id=document.id,
                chunk_id=entity_chunk.id,
                canonical_entity_id=canonical.id,
                entity_type=entity_type,
                surface_text=display_name,
                normalized_name=canonical.normalized_name,
                confidence_score=0.9,
                extraction_model="deterministic",
                extraction_metadata={"source": "seed"},
            )
        )
        graph_node = (
            db_session.query(GraphNode)
            .filter(GraphNode.canonical_entity_id == canonical.id)
            .one_or_none()
        )
        if graph_node is None:
            graph_node = GraphNode(
                space_id=space.id,
                canonical_entity_id=canonical.id,
                node_type=entity_type,
                label=display_name,
            )
            db_session.add(graph_node)
            db_session.flush()

    if len(canonical_entities) >= 2:
        source_node = db_session.query(GraphNode).filter(GraphNode.canonical_entity_id == canonical_entities[0].id).one()
        target_node = db_session.query(GraphNode).filter(GraphNode.canonical_entity_id == canonical_entities[1].id).one()
        db_session.add(
            GraphEdge(
                space_id=space.id,
                document_id=document.id,
                chunk_id=entity_chunk.id,
                source_node_id=source_node.id,
                target_node_id=target_node.id,
                relation_type="co_occurs",
                provenance_locator=f"chunk:{entity_chunk.id}",
                weight=1.0,
            )
        )

    db_session.commit()
    db_session.refresh(document)
    return document


def build_processing_runtime(api_client):
    storage = InMemoryDocumentStorage()
    queue = InMemoryDocumentProcessingQueue()
    vector_cleanup = InMemoryVectorCleanupService()
    graph_cleanup = InMemoryGraphCleanupService()
    embedding_service = DeterministicEmbeddingService()
    entity_extraction_service = DeterministicEntityExtractionService()
    api_client.app.dependency_overrides[dependency_module.get_document_storage_service] = lambda: storage
    api_client.app.dependency_overrides[dependency_module.get_document_processing_queue_service] = lambda: queue
    api_client.app.dependency_overrides[dependency_module.get_vector_cleanup] = lambda: vector_cleanup
    api_client.app.dependency_overrides[dependency_module.get_graph_cleanup] = lambda: graph_cleanup
    return storage, queue, embedding_service, entity_extraction_service
