from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from urllib.parse import urlencode
from uuid import UUID, uuid4

import pytest

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
from ragdoll.workers.document_pipeline import drain_document_jobs


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


@pytest.fixture
def retrieval_runtime(api_client):
    storage = InMemoryDocumentStorage()
    queue = InMemoryDocumentProcessingQueue()
    vector_cleanup = InMemoryVectorCleanupService()
    graph_cleanup = InMemoryGraphCleanupService()
    api_client.app.dependency_overrides[dependency_module.get_document_storage_service] = lambda: storage
    api_client.app.dependency_overrides[dependency_module.get_document_processing_queue_service] = lambda: queue
    api_client.app.dependency_overrides[dependency_module.get_vector_cleanup] = lambda: vector_cleanup
    api_client.app.dependency_overrides[dependency_module.get_graph_cleanup] = lambda: graph_cleanup
    try:
        yield storage, queue
    finally:
        api_client.app.dependency_overrides.clear()


def _completed_processing_status() -> dict[str, str | None]:
    payload = default_processing_status_payload()
    payload["overall"] = "completed"
    payload["parsing"] = "completed"
    payload["vector"] = "completed"
    payload["extraction"] = "completed"
    payload["graph"] = "completed"
    payload["detail"] = None
    return payload


def _seed_retrieval_document(
    db_session,
    *,
    space: Space,
    uploader: User,
    title: str,
    text: str,
    file_type: str = "txt",
    mime_type: str = "text/plain",
    entity_specs: list[tuple[str, str]] | None = None,
    deleted: bool = False,
) -> tuple[Document, DocumentChunk, list[CanonicalEntity]]:
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
        processing_status=_completed_processing_status(),
        chunk_count=1,
        indexed_chunk_count=1,
        deleted_at=datetime.now(timezone.utc) if deleted else None,
    )
    db_session.add(document)
    db_session.flush()

    chunk = DocumentChunk.from_text(
        document_id=document.id,
        space_id=space.id,
        chunk_index=0,
        text_content=text,
    )
    db_session.add(chunk)

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
                chunk_id=chunk.id,
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
                chunk_id=chunk.id,
                source_node_id=source_node.id,
                target_node_id=target_node.id,
                relation_type="co_occurs",
                provenance_locator=f"chunk:{chunk.id}",
                weight=1.0,
            )
        )

    db_session.commit()
    db_session.refresh(document)
    db_session.refresh(chunk)
    return document, chunk, canonical_entities


def test_search_route_requires_authentication(api_client):
    response = api_client.get("/api/v1/search?q=atlas")
    assert response.status_code == 401


def test_search_honors_scope_filters_and_deleted_documents(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    register_and_login(api_client, email="other@example.com")

    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    other = db_session.query(User).filter(User.email == "other@example.com").one()
    owner_default = default_space(db_session, owner)
    owner_second = Space(owner_user_id=owner.id, name="Second", description=None, is_default=False)
    db_session.add(owner_second)
    db_session.commit()
    db_session.refresh(owner_second)

    _seed_retrieval_document(
        db_session,
        space=owner_default,
        uploader=owner,
        title="atlas-default.txt",
        text="Atlas rollout notes for the default workspace.",
        entity_specs=[("Atlas", "project"), ("Ragdoll", "product")],
    )
    second_document, _, _ = _seed_retrieval_document(
        db_session,
        space=owner_second,
        uploader=owner,
        title="atlas-second.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        text="Atlas budget review for the second workspace.",
        entity_specs=[("Atlas", "project"), ("Budget", "topic")],
    )
    _seed_retrieval_document(
        db_session,
        space=default_space(db_session, other),
        uploader=other,
        title="atlas-other.txt",
        text="Atlas data in another owner's space.",
        entity_specs=[("Atlas", "project")],
    )
    _seed_retrieval_document(
        db_session,
        space=owner_default,
        uploader=owner,
        title="atlas-deleted.txt",
        text="Atlas content that was deleted.",
        entity_specs=[("Atlas", "project")],
        deleted=True,
    )

    default_only = api_client.get("/api/v1/search?q=atlas&mode=boolean", headers=auth_headers(token))
    assert default_only.status_code == 200, default_only.text
    assert [item["document"]["title"] for item in default_only.json()["items"]] == ["atlas-default.txt"]

    across_spaces = api_client.get(
        "/api/v1/search?q=atlas&mode=boolean&all_spaces=true",
        headers=auth_headers(token),
    )
    assert across_spaces.status_code == 200, across_spaces.text
    assert [item["document"]["title"] for item in across_spaces.json()["items"]] == [
        "atlas-second.pdf",
        "atlas-default.txt",
    ]

    second_only = api_client.get(
        f"/api/v1/search?q=atlas&mode=boolean&space_id={owner_second.id}",
        headers=auth_headers(token),
    )
    assert second_only.status_code == 200, second_only.text
    assert [item["document"]["title"] for item in second_only.json()["items"]] == ["atlas-second.pdf"]

    filtered = api_client.get(
        f"/api/v1/search?q=atlas&mode=boolean&all_spaces=true&file_type=pdf&document_id={second_document.id}&entity_type=project",
        headers=auth_headers(token),
    )
    assert filtered.status_code == 200, filtered.text
    assert [item["document"]["title"] for item in filtered.json()["items"]] == ["atlas-second.pdf"]


def test_search_modes_return_ranked_results_with_citations(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()

    _seed_retrieval_document(
        db_session,
        space=default_space(db_session, owner),
        uploader=owner,
        title="atlas-notes.txt",
        text="Project Atlas works closely with Ragdoll.",
        entity_specs=[("Project Atlas", "project"), ("Ragdoll", "product")],
    )

    boolean_response = api_client.get("/api/v1/search?q=atlas&mode=boolean", headers=auth_headers(token))
    assert boolean_response.status_code == 200, boolean_response.text
    boolean_item = boolean_response.json()["items"][0]
    assert boolean_item["result_kind"] == "document_chunk"
    assert boolean_item["citations"][0]["source_tier"] == "document"

    vector_response = api_client.get("/api/v1/search?q=atlas&mode=vector", headers=auth_headers(token))
    assert vector_response.status_code == 200, vector_response.text
    assert vector_response.json()["items"][0]["document"]["title"] == "atlas-notes.txt"

    graph_response = api_client.get("/api/v1/search?q=atlas&mode=graph", headers=auth_headers(token))
    assert graph_response.status_code == 200, graph_response.text
    graph_item = graph_response.json()["items"][0]
    assert graph_item["result_kind"] == "entity"
    assert graph_item["entity"]["display_name"] == "Project Atlas"
    assert graph_item["citations"][0]["source_tier"] == "derived"

    combined_response = api_client.get("/api/v1/search?q=atlas&mode=combined", headers=auth_headers(token))
    assert combined_response.status_code == 200, combined_response.text
    combined_items = combined_response.json()["items"]
    chunk_item = next(item for item in combined_items if item["result_kind"] == "document_chunk")
    assert set(chunk_item["matched_modes"]) >= {"boolean", "vector"}


def test_processed_upload_becomes_searchable_entity_readable_and_graph_readable(
    api_client,
    db_session,
    retrieval_runtime,
):
    storage, queue = retrieval_runtime
    token = register_and_login(api_client, email="owner@example.com")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("atlas.txt", BytesIO(b"Project Atlas works with Ragdoll"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text

    assert (
        drain_document_jobs(
            queue=queue,
            storage=storage,
            embedding_service=DeterministicEmbeddingService(),
            entity_extraction_service=DeterministicEntityExtractionService(),
        )
        == 1
    )

    search_response = api_client.get("/api/v1/search?q=Atlas&mode=combined", headers=auth_headers(token))
    assert search_response.status_code == 200, search_response.text
    assert any(item["document"]["title"] == "atlas.txt" for item in search_response.json()["items"])

    entities_response = api_client.get("/api/v1/entities?q=atlas", headers=auth_headers(token))
    assert entities_response.status_code == 200, entities_response.text
    atlas_entity = next(item for item in entities_response.json()["items"] if "atlas" in item["display_name"].lower())

    graph_response = api_client.get(
        f"/api/v1/knowledge-graph/entities/{atlas_entity['id']}/subgraph",
        headers=auth_headers(token),
    )
    assert graph_response.status_code == 200, graph_response.text
    graph_payload = graph_response.json()
    assert len(graph_payload["nodes"]) >= 2
    assert len(graph_payload["links"]) >= 1
