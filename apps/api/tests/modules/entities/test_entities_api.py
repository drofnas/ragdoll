from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlencode

from ragdoll.platform.db.models import CanonicalEntity, Document, DocumentChunk, Entity, GraphNode, Space, User
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


def _seed_entity_document(db_session, *, space: Space, uploader: User, title: str, text: str, deleted: bool = False):
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
    db_session.flush()
    return document, chunk


def test_entity_routes_require_authentication(api_client):
    response = api_client.get("/api/v1/entities")
    assert response.status_code == 401


def test_entities_list_uses_default_scope_and_all_spaces(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    owner_default = default_space(db_session, owner)
    owner_second = Space(owner_user_id=owner.id, name="Second", description=None, is_default=False)
    db_session.add(owner_second)
    db_session.commit()
    db_session.refresh(owner_second)

    default_document, default_chunk = _seed_entity_document(
        db_session,
        space=owner_default,
        uploader=owner,
        title="default.txt",
        text="Atlas entry",
    )
    second_document, second_chunk = _seed_entity_document(
        db_session,
        space=owner_second,
        uploader=owner,
        title="second.txt",
        text="Phoenix entry",
    )
    atlas = CanonicalEntity(
        space_id=owner_default.id,
        entity_type="project",
        normalized_name=normalize_entity_name("Atlas"),
        display_name="Atlas",
    )
    phoenix = CanonicalEntity(
        space_id=owner_second.id,
        entity_type="project",
        normalized_name=normalize_entity_name("Phoenix"),
        display_name="Phoenix",
    )
    db_session.add_all([atlas, phoenix])
    db_session.flush()
    db_session.add_all(
        [
            GraphNode(space_id=owner_default.id, canonical_entity_id=atlas.id, node_type="project", label="Atlas"),
            GraphNode(space_id=owner_second.id, canonical_entity_id=phoenix.id, node_type="project", label="Phoenix"),
            Entity(
                space_id=owner_default.id,
                document_id=default_document.id,
                chunk_id=default_chunk.id,
                canonical_entity_id=atlas.id,
                entity_type="project",
                surface_text="Atlas",
                normalized_name=atlas.normalized_name,
                confidence_score=0.9,
                extraction_model="seed",
                extraction_metadata={"source": "seed"},
            ),
            Entity(
                space_id=owner_second.id,
                document_id=second_document.id,
                chunk_id=second_chunk.id,
                canonical_entity_id=phoenix.id,
                entity_type="project",
                surface_text="Phoenix",
                normalized_name=phoenix.normalized_name,
                confidence_score=0.9,
                extraction_model="seed",
                extraction_metadata={"source": "seed"},
            ),
        ]
    )
    db_session.commit()

    default_response = api_client.get("/api/v1/entities", headers=auth_headers(token))
    assert default_response.status_code == 200, default_response.text
    assert [item["display_name"] for item in default_response.json()["items"]] == ["Atlas"]

    all_spaces_response = api_client.get("/api/v1/entities?all_spaces=true", headers=auth_headers(token))
    assert all_spaces_response.status_code == 200, all_spaces_response.text
    assert [item["display_name"] for item in all_spaces_response.json()["items"]] == ["Atlas", "Phoenix"]


def test_entity_detail_returns_provenance_history_and_related_documents(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    owner_default = default_space(db_session, owner)

    first_document, first_chunk = _seed_entity_document(
        db_session,
        space=owner_default,
        uploader=owner,
        title="first.txt",
        text="Atlas first mention",
    )
    second_document, second_chunk = _seed_entity_document(
        db_session,
        space=owner_default,
        uploader=owner,
        title="second.txt",
        text="Atlas second mention",
    )
    deleted_document, deleted_chunk = _seed_entity_document(
        db_session,
        space=owner_default,
        uploader=owner,
        title="deleted.txt",
        text="Atlas deleted mention",
        deleted=True,
    )

    atlas = CanonicalEntity(
        space_id=owner_default.id,
        entity_type="project",
        normalized_name=normalize_entity_name("Atlas"),
        display_name="Atlas",
    )
    db_session.add(atlas)
    db_session.flush()
    db_session.add(GraphNode(space_id=owner_default.id, canonical_entity_id=atlas.id, node_type="project", label="Atlas"))
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
                confidence_score=0.9,
                extraction_model="seed",
                extraction_metadata={"order": 1},
            ),
            Entity(
                space_id=owner_default.id,
                document_id=second_document.id,
                chunk_id=second_chunk.id,
                canonical_entity_id=atlas.id,
                entity_type="project",
                surface_text="Atlas",
                normalized_name=atlas.normalized_name,
                confidence_score=0.85,
                extraction_model="seed",
                extraction_metadata={"order": 2},
            ),
            Entity(
                space_id=owner_default.id,
                document_id=deleted_document.id,
                chunk_id=deleted_chunk.id,
                canonical_entity_id=atlas.id,
                entity_type="project",
                surface_text="Atlas",
                normalized_name=atlas.normalized_name,
                confidence_score=0.5,
                extraction_model="seed",
                extraction_metadata={"order": 3},
            ),
        ]
    )
    db_session.commit()

    detail_response = api_client.get(f"/api/v1/entities/{atlas.id}", headers=auth_headers(token))
    assert detail_response.status_code == 200, detail_response.text
    payload = detail_response.json()
    assert payload["id"] == str(atlas.id)
    assert payload["graph_node_id"] is not None
    assert [entry["document_id"] for entry in payload["history"]] == [str(first_document.id), str(second_document.id)]
    assert len(payload["provenance"]) == 2
    assert [item["title"] for item in payload["related_documents"]] == ["second.txt", "first.txt"]
    assert all(item["title"] != "deleted.txt" for item in payload["related_documents"])
