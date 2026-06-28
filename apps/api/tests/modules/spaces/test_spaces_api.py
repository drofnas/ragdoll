from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlencode
from uuid import uuid4

from ragdoll.platform.db.models import Document, PinnedFact, Space, User
from ragdoll.platform.db.models.documents import default_processing_status_payload


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


def test_spaces_routes_require_authentication(api_client):
    responses = [
        api_client.get("/api/v1/spaces"),
        api_client.post("/api/v1/spaces", json={"name": "Architecture"}),
        api_client.get(f"/api/v1/spaces/{uuid4()}"),
        api_client.patch(f"/api/v1/spaces/{uuid4()}", json={"name": "Updated"}),
        api_client.delete(f"/api/v1/spaces/{uuid4()}"),
    ]

    assert all(response.status_code == 401 for response in responses)


def test_create_list_and_read_space(api_client):
    token = register_and_login(api_client)

    created = api_client.post(
        "/api/v1/spaces",
        json={"name": "Architecture", "description": "ADR corpus"},
        headers=auth_headers(token),
    )

    assert created.status_code == 201, created.text
    created_body = created.json()
    assert created_body["name"] == "Architecture"
    assert created_body["is_default"] is False
    assert created_body["document_count"] == 0
    assert created_body["pinned_fact_count"] == 0

    listed = api_client.get("/api/v1/spaces", headers=auth_headers(token))
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["items"]) == 2
    assert all("document_count" in item for item in listed.json()["items"])
    assert all("pinned_fact_count" in item for item in listed.json()["items"])

    loaded = api_client.get(f"/api/v1/spaces/{created_body['id']}", headers=auth_headers(token))
    assert loaded.status_code == 200
    assert loaded.json()["id"] == created_body["id"]
    assert loaded.json()["document_count"] == 0
    assert loaded.json()["pinned_fact_count"] == 0


def test_spaces_list_includes_document_and_pinned_fact_counts(api_client, db_session):
    token = register_and_login(api_client)
    owner = db_session.query(User).filter(User.email == "user@example.com").one()
    default_space = (
        db_session.query(Space)
        .filter(Space.owner_user_id == owner.id, Space.is_default.is_(True))
        .one()
    )
    second_space = Space(owner_user_id=owner.id, name="Second", description=None, is_default=False)
    db_session.add(second_space)
    db_session.flush()

    status = default_processing_status_payload()
    db_session.add_all(
        [
            Document(
                space_id=default_space.id,
                uploaded_by=owner.id,
                title="One",
                original_filename="one.txt",
                mime_type="text/plain",
                file_type="txt",
                file_size=10,
                storage_key="documents/one.txt",
                source_kind="manual_upload",
                processing_status=status,
            ),
            Document(
                space_id=default_space.id,
                uploaded_by=owner.id,
                title="Two",
                original_filename="two.txt",
                mime_type="text/plain",
                file_type="txt",
                file_size=10,
                storage_key="documents/two.txt",
                source_kind="manual_upload",
                processing_status=status,
            ),
            Document(
                space_id=default_space.id,
                uploaded_by=owner.id,
                title="Deleted",
                original_filename="deleted.txt",
                mime_type="text/plain",
                file_type="txt",
                file_size=10,
                storage_key="documents/deleted.txt",
                source_kind="manual_upload",
                processing_status=status,
                deleted_at=datetime.now(timezone.utc),
            ),
            Document(
                space_id=second_space.id,
                uploaded_by=owner.id,
                title="Three",
                original_filename="three.txt",
                mime_type="text/plain",
                file_type="txt",
                file_size=10,
                storage_key="documents/three.txt",
                source_kind="manual_upload",
                processing_status=status,
            ),
            PinnedFact(
                space_id=default_space.id,
                owner_user_id=owner.id,
                key="focus_project",
                title="Focus Project",
                description="Project",
                value_kind="text",
                value_text="Atlas",
                status="active",
            ),
            PinnedFact(
                space_id=default_space.id,
                owner_user_id=owner.id,
                key="sponsor",
                title="Sponsor",
                description="Sponsor",
                value_kind="text",
                value_text="Acme",
                status="active",
            ),
            PinnedFact(
                space_id=second_space.id,
                owner_user_id=owner.id,
                key="release",
                title="Release",
                description="Release",
                value_kind="text",
                value_text="Soon",
                status="active",
            ),
        ]
    )
    db_session.commit()

    listed = api_client.get("/api/v1/spaces?include_archived=true", headers=auth_headers(token))
    assert listed.status_code == 200, listed.text
    by_id = {item["id"]: item for item in listed.json()["items"]}

    assert by_id[str(default_space.id)]["document_count"] == 2
    assert by_id[str(default_space.id)]["pinned_fact_count"] == 2
    assert by_id[str(second_space.id)]["document_count"] == 1
    assert by_id[str(second_space.id)]["pinned_fact_count"] == 1

    loaded = api_client.get(f"/api/v1/spaces/{default_space.id}", headers=auth_headers(token))
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["document_count"] == 2
    assert loaded.json()["pinned_fact_count"] == 2


def test_update_and_archive_non_default_space(api_client):
    token = register_and_login(api_client)
    created = api_client.post(
        "/api/v1/spaces",
        json={"name": "Architecture", "description": "ADR corpus"},
        headers=auth_headers(token),
    ).json()

    updated = api_client.patch(
        f"/api/v1/spaces/{created['id']}",
        json={"name": "Updated", "description": "Updated description"},
        headers=auth_headers(token),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Updated"

    archived = api_client.delete(f"/api/v1/spaces/{created['id']}", headers=auth_headers(token))
    assert archived.status_code == 200, archived.text
    assert archived.json()["archived_at"] is not None

    visible = api_client.get("/api/v1/spaces", headers=auth_headers(token))
    with_archived = api_client.get("/api/v1/spaces?include_archived=true", headers=auth_headers(token))
    assert len(visible.json()["items"]) == 1
    assert len(with_archived.json()["items"]) == 2


def test_space_owner_isolation_returns_404(api_client):
    token_a = register_and_login(api_client, email="owner@example.com")
    token_b = register_and_login(api_client, email="other@example.com")

    created = api_client.post(
        "/api/v1/spaces",
        json={"name": "Owner Space"},
        headers=auth_headers(token_a),
    ).json()

    responses = [
        api_client.get(f"/api/v1/spaces/{created['id']}", headers=auth_headers(token_b)),
        api_client.patch(f"/api/v1/spaces/{created['id']}", json={"name": "Nope"}, headers=auth_headers(token_b)),
        api_client.delete(f"/api/v1/spaces/{created['id']}", headers=auth_headers(token_b)),
    ]

    assert all(response.status_code == 404 for response in responses)


def test_default_space_can_be_reassigned_and_remains_single_default(api_client):
    token = register_and_login(api_client)
    created = api_client.post(
        "/api/v1/spaces",
        json={"name": "Secondary Space"},
        headers=auth_headers(token),
    ).json()

    updated = api_client.patch(
        f"/api/v1/spaces/{created['id']}",
        json={"is_default": True},
        headers=auth_headers(token),
    )

    assert updated.status_code == 200, updated.text
    spaces = api_client.get("/api/v1/spaces?include_archived=true", headers=auth_headers(token)).json()["items"]
    default_spaces = [space for space in spaces if space["is_default"]]
    assert len(default_spaces) == 1
    assert default_spaces[0]["id"] == created["id"]


def test_default_space_cannot_be_archived_or_unset(api_client):
    token = register_and_login(api_client)
    default_space = api_client.get("/api/v1/spaces", headers=auth_headers(token)).json()["items"][0]

    archive_response = api_client.delete(f"/api/v1/spaces/{default_space['id']}", headers=auth_headers(token))
    unset_response = api_client.patch(
        f"/api/v1/spaces/{default_space['id']}",
        json={"is_default": False},
        headers=auth_headers(token),
    )

    assert archive_response.status_code == 403
    assert archive_response.json()["code"] == "default_space_cannot_be_archived"
    assert unset_response.status_code == 422
    assert unset_response.json()["code"] == "request_validation_failed"
