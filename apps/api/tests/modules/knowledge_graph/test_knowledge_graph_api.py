from __future__ import annotations

from urllib.parse import urlencode

from ragdoll.platform.db.models import CanonicalEntity, Document, DocumentChunk, Entity, GraphEdge, GraphNode, Space, User
from ragdoll.platform.db.models.documents import default_processing_status_payload
from ragdoll.platform.llm import normalize_entity_name


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


def _completed_processing_status() -> dict[str, str | None]:
    payload = default_processing_status_payload()
    payload["overall"] = "completed"
    payload["parsing"] = "completed"
    payload["vector"] = "completed"
    payload["extraction"] = "completed"
    payload["graph"] = "completed"
    payload["detail"] = None
    return payload


def _seed_document(db_session, *, space: Space, uploader: User, title: str, text: str) -> tuple[Document, DocumentChunk]:
    document = Document(
        space_id=space.id,
        uploaded_by=uploader.id,
        title=title,
        original_filename=title,
        mime_type="text/plain",
        file_type="txt",
        file_size=len(text.encode("utf-8")),
        storage_key=f"documents/{space.id}/{title}",
        source_kind="manual_upload",
        preview_text=text[:280],
        original_text_content=text,
        processing_status=_completed_processing_status(),
        chunk_count=1,
        indexed_chunk_count=1,
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
    db_session.flush()
    return document, chunk


def test_knowledge_graph_routes_require_authentication(api_client):
    response = api_client.get(f"/api/v1/knowledge-graph/entities/{User.__name__}/subgraph")
    assert response.status_code in {401, 422}


def test_entity_subgraph_and_document_graph_reads(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    owner_default = default_space(db_session, owner)

    first_document, first_chunk = _seed_document(
        db_session,
        space=owner_default,
        uploader=owner,
        title="first.txt",
        text="Atlas and Ragdoll",
    )
    second_document, second_chunk = _seed_document(
        db_session,
        space=owner_default,
        uploader=owner,
        title="second.txt",
        text="Ragdoll and Phoenix",
    )
    atlas = CanonicalEntity(
        space_id=owner_default.id,
        entity_type="project",
        normalized_name=normalize_entity_name("Atlas"),
        display_name="Atlas",
    )
    ragdoll = CanonicalEntity(
        space_id=owner_default.id,
        entity_type="product",
        normalized_name=normalize_entity_name("Ragdoll"),
        display_name="Ragdoll",
    )
    phoenix = CanonicalEntity(
        space_id=owner_default.id,
        entity_type="project",
        normalized_name=normalize_entity_name("Phoenix"),
        display_name="Phoenix",
    )
    db_session.add_all([atlas, ragdoll, phoenix])
    db_session.flush()

    atlas_node = GraphNode(space_id=owner_default.id, canonical_entity_id=atlas.id, node_type="project", label="Atlas")
    ragdoll_node = GraphNode(
        space_id=owner_default.id,
        canonical_entity_id=ragdoll.id,
        node_type="product",
        label="Ragdoll",
    )
    phoenix_node = GraphNode(
        space_id=owner_default.id,
        canonical_entity_id=phoenix.id,
        node_type="project",
        label="Phoenix",
    )
    db_session.add_all([atlas_node, ragdoll_node, phoenix_node])
    db_session.flush()

    db_session.add_all(
        [
            Entity(
                space_id=owner_default.id,
                document_id=first_document.id,
                chunk_id=first_chunk.id,
                canonical_entity_id=atlas.id,
                entity_type="project",
                surface_text="Atlas",
                normalized_name=atlas.normalized_name,
            ),
            Entity(
                space_id=owner_default.id,
                document_id=first_document.id,
                chunk_id=first_chunk.id,
                canonical_entity_id=ragdoll.id,
                entity_type="product",
                surface_text="Ragdoll",
                normalized_name=ragdoll.normalized_name,
            ),
            Entity(
                space_id=owner_default.id,
                document_id=second_document.id,
                chunk_id=second_chunk.id,
                canonical_entity_id=ragdoll.id,
                entity_type="product",
                surface_text="Ragdoll",
                normalized_name=ragdoll.normalized_name,
            ),
            Entity(
                space_id=owner_default.id,
                document_id=second_document.id,
                chunk_id=second_chunk.id,
                canonical_entity_id=phoenix.id,
                entity_type="project",
                surface_text="Phoenix",
                normalized_name=phoenix.normalized_name,
            ),
            GraphEdge(
                space_id=owner_default.id,
                document_id=first_document.id,
                chunk_id=first_chunk.id,
                source_node_id=atlas_node.id,
                target_node_id=ragdoll_node.id,
                relation_type="co_occurs",
                provenance_locator=f"chunk:{first_chunk.id}",
                weight=1.0,
            ),
            GraphEdge(
                space_id=owner_default.id,
                document_id=second_document.id,
                chunk_id=second_chunk.id,
                source_node_id=ragdoll_node.id,
                target_node_id=phoenix_node.id,
                relation_type="co_occurs",
                provenance_locator=f"chunk:{second_chunk.id}",
                weight=1.0,
            ),
        ]
    )
    db_session.commit()

    subgraph = api_client.get(
        f"/api/v1/knowledge-graph/entities/{ragdoll.id}/subgraph?depth=2&limit=2",
        headers=auth_headers(token),
    )
    assert subgraph.status_code == 200, subgraph.text
    subgraph_payload = subgraph.json()
    assert {node["id"] for node in subgraph_payload["nodes"]} >= {str(ragdoll.id), str(atlas.id)}
    assert len(subgraph_payload["links"]) == 2

    limited = api_client.get(
        f"/api/v1/knowledge-graph/entities/{ragdoll.id}/subgraph?depth=2&limit=1",
        headers=auth_headers(token),
    )
    assert limited.status_code == 200, limited.text
    assert len(limited.json()["links"]) == 1

    document_graph = api_client.get(
        f"/api/v1/knowledge-graph/documents/{first_document.id}",
        headers=auth_headers(token),
    )
    assert document_graph.status_code == 200, document_graph.text
    assert len(document_graph.json()["links"]) == 1


def test_document_graph_returns_typed_empty_graph(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    owner_default = default_space(db_session, owner)
    document, _ = _seed_document(
        db_session,
        space=owner_default,
        uploader=owner,
        title="empty.txt",
        text="No graph edges yet",
    )
    db_session.commit()

    response = api_client.get(f"/api/v1/knowledge-graph/documents/{document.id}", headers=auth_headers(token))
    assert response.status_code == 200, response.text
    assert response.json()["nodes"] == []
    assert response.json()["links"] == []
