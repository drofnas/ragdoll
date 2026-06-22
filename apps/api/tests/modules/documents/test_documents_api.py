from __future__ import annotations

from datetime import datetime, timedelta, timezone
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


@pytest.fixture
def document_runtime(api_client):
    storage = InMemoryDocumentStorage()
    vector_cleanup = InMemoryVectorCleanupService()
    graph_cleanup = InMemoryGraphCleanupService()
    api_client.app.dependency_overrides[dependency_module.get_document_storage_service] = lambda: storage
    api_client.app.dependency_overrides[dependency_module.get_vector_cleanup] = lambda: vector_cleanup
    api_client.app.dependency_overrides[dependency_module.get_graph_cleanup] = lambda: graph_cleanup
    try:
        yield storage, vector_cleanup, graph_cleanup
    finally:
        api_client.app.dependency_overrides.clear()


@pytest.fixture
def storage_only_runtime(api_client):
    storage = InMemoryDocumentStorage()
    api_client.app.dependency_overrides[dependency_module.get_document_storage_service] = lambda: storage
    try:
        yield storage
    finally:
        api_client.app.dependency_overrides.clear()


def _default_space(db_session, user: User) -> Space:
    return (
        db_session.query(Space)
        .filter(Space.owner_user_id == user.id, Space.is_default.is_(True))
        .one()
    )


def _seed_document(
    db_session,
    *,
    space: Space,
    uploader: User,
    title: str,
    storage_key: str,
    file_type: str = "txt",
    mime_type: str = "text/plain",
    file_size: int = 128,
    created_at: datetime | None = None,
    processing_overall: str = "completed",
) -> Document:
    payload = default_processing_status_payload()
    payload["overall"] = processing_overall
    document = Document(
        space_id=space.id,
        uploaded_by=uploader.id,
        title=title,
        original_filename=title,
        mime_type=mime_type,
        file_type=file_type,
        file_size=file_size,
        storage_key=storage_key,
        source_kind="manual_upload",
        preview_text=f"Preview for {title}",
        original_text_content=f"Original for {title}",
        processing_status=payload,
        chunk_count=3,
        indexed_chunk_count=3 if processing_overall == "completed" else 1,
        created_at=created_at or datetime.now(timezone.utc),
        updated_at=created_at or datetime.now(timezone.utc),
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def test_document_routes_require_authentication(api_client):
    document_id = uuid4()
    responses = [
        api_client.get("/api/v1/documents"),
        api_client.get(f"/api/v1/documents/{document_id}"),
        api_client.patch(f"/api/v1/documents/{document_id}", json={"space_id": str(uuid4())}),
        api_client.delete(f"/api/v1/documents/{document_id}"),
        api_client.get(f"/api/v1/documents/{document_id}/download"),
    ]

    assert all(response.status_code == 401 for response in responses)


def test_list_documents_filters_and_owner_isolation(api_client, db_session, document_runtime):
    storage, _, _ = document_runtime
    token = register_and_login(api_client, email="owner@example.com")
    register_and_login(api_client, email="other@example.com")

    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    other = db_session.query(User).filter(User.email == "other@example.com").one()
    owner_space = _default_space(db_session, owner)
    other_space = _default_space(db_session, other)
    second_space = Space(owner_user_id=owner.id, name="Second Space", description=None, is_default=False)
    db_session.add(second_space)
    db_session.commit()
    db_session.refresh(second_space)

    older = _seed_document(
        db_session,
        space=owner_space,
        uploader=owner,
        title="older.txt",
        storage_key="documents/older.txt",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    newer = _seed_document(
        db_session,
        space=second_space,
        uploader=owner,
        title="newer.pdf",
        storage_key="documents/newer.pdf",
        file_type="pdf",
        mime_type="application/pdf",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )
    _seed_document(
        db_session,
        space=other_space,
        uploader=other,
        title="other.txt",
        storage_key="documents/other.txt",
    )
    storage.seed_original_file(older.storage_key, b"older")
    storage.seed_original_file(newer.storage_key, b"newer")

    response = api_client.get("/api/v1/documents", headers=auth_headers(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 2
    assert [item["title"] for item in body["items"]] == ["newer.pdf", "older.txt"]

    filtered = api_client.get(
        f"/api/v1/documents?space_id={owner_space.id}&uploaded_by=me&date_to=2026-01-01T23:59:59Z",
        headers=auth_headers(token),
    )
    assert filtered.status_code == 200, filtered.text
    assert [item["title"] for item in filtered.json()["items"]] == ["older.txt"]

    pdf_only = api_client.get("/api/v1/documents?file_type=pdf", headers=auth_headers(token))
    assert pdf_only.status_code == 200
    assert [item["title"] for item in pdf_only.json()["items"]] == ["newer.pdf"]


def test_document_detail_and_download_enforce_visibility(api_client, db_session, document_runtime):
    storage, _, _ = document_runtime
    token_a = register_and_login(api_client, email="owner@example.com")
    token_b = register_and_login(api_client, email="other@example.com")

    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    other = db_session.query(User).filter(User.email == "other@example.com").one()
    owner_doc = _seed_document(
        db_session,
        space=_default_space(db_session, owner),
        uploader=owner,
        title="visible.txt",
        storage_key="documents/visible.txt",
    )
    other_doc = _seed_document(
        db_session,
        space=_default_space(db_session, other),
        uploader=other,
        title="hidden.txt",
        storage_key="documents/hidden.txt",
    )
    storage.seed_original_file(owner_doc.storage_key, b"visible-bytes")
    storage.seed_original_file(other_doc.storage_key, b"hidden-bytes")

    detail = api_client.get(f"/api/v1/documents/{owner_doc.id}", headers=auth_headers(token_a))
    assert detail.status_code == 200, detail.text
    assert detail.json()["preview_text"] == "Preview for visible.txt"

    download = api_client.get(f"/api/v1/documents/{owner_doc.id}/download", headers=auth_headers(token_a))
    assert download.status_code == 200, download.text
    assert download.content == b"visible-bytes"
    assert "attachment;" in download.headers["content-disposition"]

    forbidden_detail = api_client.get(f"/api/v1/documents/{owner_doc.id}", headers=auth_headers(token_b))
    forbidden_download = api_client.get(f"/api/v1/documents/{owner_doc.id}/download", headers=auth_headers(token_b))
    assert forbidden_detail.status_code == 404
    assert forbidden_download.status_code == 404


def test_patch_document_moves_between_owned_spaces_and_rejects_invalid_targets(api_client, db_session, document_runtime):
    document_runtime
    token = register_and_login(api_client, email="owner@example.com")
    token_other = register_and_login(api_client, email="other@example.com")

    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    other = db_session.query(User).filter(User.email == "other@example.com").one()
    owner_default = _default_space(db_session, owner)
    other_default = _default_space(db_session, other)
    destination = Space(owner_user_id=owner.id, name="Destination", description=None, is_default=False)
    archived = Space(
        owner_user_id=owner.id,
        name="Archived",
        description=None,
        is_default=False,
        archived_at=datetime.now(timezone.utc),
    )
    db_session.add_all([destination, archived])
    db_session.commit()
    db_session.refresh(destination)
    db_session.refresh(archived)

    document = _seed_document(
        db_session,
        space=owner_default,
        uploader=owner,
        title="movable.txt",
        storage_key="documents/movable.txt",
    )

    moved = api_client.patch(
        f"/api/v1/documents/{document.id}",
        json={"space_id": str(destination.id)},
        headers=auth_headers(token),
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["space_id"] == str(destination.id)

    archived_target = api_client.patch(
        f"/api/v1/documents/{document.id}",
        json={"space_id": str(archived.id)},
        headers=auth_headers(token),
    )
    assert archived_target.status_code == 409
    assert archived_target.json()["code"] == "document_destination_space_archived"

    foreign_target = api_client.patch(
        f"/api/v1/documents/{document.id}",
        json={"space_id": str(other_default.id)},
        headers=auth_headers(token),
    )
    assert foreign_target.status_code == 404

    foreign_actor = api_client.patch(
        f"/api/v1/documents/{document.id}",
        json={"space_id": str(other_default.id)},
        headers=auth_headers(token_other),
    )
    assert foreign_actor.status_code == 404


def test_delete_document_soft_deletes_and_cleans_up_artifacts(api_client, db_session, document_runtime):
    storage, vector_cleanup, graph_cleanup = document_runtime
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    document = _seed_document(
        db_session,
        space=_default_space(db_session, owner),
        uploader=owner,
        title="delete-me.txt",
        storage_key="documents/delete-me.txt",
    )
    storage.seed_original_file(document.storage_key, b"delete-me")

    deleted = api_client.delete(f"/api/v1/documents/{document.id}", headers=auth_headers(token))
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["success"] is True

    db_session.expire_all()
    stored = db_session.query(Document).filter(Document.id == document.id).one()
    assert stored.deleted_at is not None
    assert document.id in vector_cleanup.cleaned_document_ids
    assert document.id in graph_cleanup.cleaned_document_ids
    assert document.storage_key not in storage.originals

    listed = api_client.get("/api/v1/documents", headers=auth_headers(token))
    assert listed.status_code == 200
    assert listed.json()["total"] == 0

    missing = api_client.get(f"/api/v1/documents/{document.id}", headers=auth_headers(token))
    assert missing.status_code == 404


def test_download_returns_conflict_when_blob_is_missing(api_client, db_session, document_runtime):
    document_runtime
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    document = _seed_document(
        db_session,
        space=_default_space(db_session, owner),
        uploader=owner,
        title="missing.txt",
        storage_key="documents/missing.txt",
    )

    response = api_client.get(f"/api/v1/documents/{document.id}/download", headers=auth_headers(token))
    assert response.status_code == 409
    assert response.json()["code"] == "document_blob_missing"


def test_delete_document_removes_retrieval_projections_with_sql_cleanup(api_client, db_session, storage_only_runtime):
    storage = storage_only_runtime
    token = register_and_login(api_client, email="projection-owner@example.com")
    owner = db_session.query(User).filter(User.email == "projection-owner@example.com").one()
    document = _seed_document(
        db_session,
        space=_default_space(db_session, owner),
        uploader=owner,
        title="projection.txt",
        storage_key="documents/projection.txt",
    )
    storage.seed_original_file(document.storage_key, b"projection")

    chunk = DocumentChunk.from_text(
        document_id=document.id,
        space_id=document.space_id,
        chunk_index=0,
        text_content="Project Atlas Ragdoll",
    )
    canonical_a = CanonicalEntity(
        space_id=document.space_id,
        entity_type="proper_noun",
        normalized_name="project atlas",
        display_name="Project Atlas",
    )
    canonical_b = CanonicalEntity(
        space_id=document.space_id,
        entity_type="proper_noun",
        normalized_name="ragdoll",
        display_name="Ragdoll",
    )
    db_session.add_all([chunk, canonical_a, canonical_b])
    db_session.flush()
    node_a = GraphNode(space_id=document.space_id, canonical_entity_id=canonical_a.id, node_type="proper_noun", label="Project Atlas")
    node_b = GraphNode(space_id=document.space_id, canonical_entity_id=canonical_b.id, node_type="proper_noun", label="Ragdoll")
    db_session.add_all([node_a, node_b])
    db_session.flush()
    db_session.add(
        DocumentChunkVector(
            chunk_id=chunk.id,
            document_id=document.id,
            space_id=document.space_id,
            chunk_index=0,
            checksum=chunk.checksum,
            embedding_model="deterministic",
            embedding_dimensions=2,
            embedding=[0.1, 0.2],
        )
    )
    db_session.add_all(
        [
            Entity(
                space_id=document.space_id,
                document_id=document.id,
                chunk_id=chunk.id,
                canonical_entity_id=canonical_a.id,
                entity_type="proper_noun",
                surface_text="Project Atlas",
                normalized_name="project atlas",
            ),
            Entity(
                space_id=document.space_id,
                document_id=document.id,
                chunk_id=chunk.id,
                canonical_entity_id=canonical_b.id,
                entity_type="proper_noun",
                surface_text="Ragdoll",
                normalized_name="ragdoll",
            ),
            GraphEdge(
                space_id=document.space_id,
                document_id=document.id,
                chunk_id=chunk.id,
                source_node_id=node_a.id,
                target_node_id=node_b.id,
                relation_type="co_occurs",
                provenance_locator=f"chunk:{chunk.id}",
                weight=1.0,
            ),
        ]
    )
    db_session.commit()

    deleted = api_client.delete(f"/api/v1/documents/{document.id}", headers=auth_headers(token))
    assert deleted.status_code == 200, deleted.text

    db_session.expire_all()
    assert db_session.query(DocumentChunkVector).filter(DocumentChunkVector.document_id == document.id).count() == 0
    assert db_session.query(Entity).filter(Entity.document_id == document.id).count() == 0
    assert db_session.query(GraphEdge).filter(GraphEdge.document_id == document.id).count() == 0
    assert db_session.query(GraphNode).count() == 0
    assert db_session.query(CanonicalEntity).count() == 0
