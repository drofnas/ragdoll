from __future__ import annotations

from urllib.parse import urlencode

from ragdoll.api import dependencies as dependency_module
from ragdoll.core.config import Settings
from ragdoll.platform.db.models import CorrectionRecord, Document, Space, UsageEvent, User, UserUsageSnapshot
from ragdoll.platform.graph.service import InMemoryGraphCleanupService
from ragdoll.platform.storage.service import InMemoryDocumentStorage
from ragdoll.platform.vector.service import InMemoryVectorCleanupService


def register_user(api_client, *, email: str = "user@example.com", password: str = "testpass123", full_name: str = "Test User"):
    return api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )


def login_user(api_client, *, email: str = "user@example.com", password: str = "testpass123"):
    return api_client.post(
        "/api/v1/auth/login",
        content=urlencode({"username": email, "password": password}),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_register_creates_user_profile_and_default_space(api_client):
    response = register_user(api_client)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["email"] == "user@example.com"
    assert "plan_tier" not in body
    assert "feature_flags" not in body

    login = login_user(api_client)
    token = login.json()["access_token"]
    spaces = api_client.get("/api/v1/spaces", headers=auth_headers(token))
    assert spaces.status_code == 200, spaces.text
    items = spaces.json()["items"]
    assert len(items) == 1
    assert items[0]["is_default"] is True


def test_register_rejects_duplicate_email(api_client):
    first = register_user(api_client)
    second = register_user(api_client)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "email_already_registered"


def test_login_updates_last_login_and_returns_token(api_client, db_session):
    register_user(api_client)

    response = login_user(api_client)

    assert response.status_code == 200, response.text
    assert response.json()["token_type"] == "bearer"
    user = db_session.query(User).filter(User.email == "user@example.com").one()
    assert user.last_login is not None


def test_login_rejects_incorrect_password(api_client):
    register_user(api_client)

    response = login_user(api_client, password="wrongpass123")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


def test_me_requires_authentication(api_client):
    response = api_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


def test_me_returns_minimal_profile_contract(api_client, db_session):
    register_user(api_client)
    login = login_user(api_client)
    token = login.json()["access_token"]
    response = api_client.get("/api/v1/auth/me", headers=auth_headers(token))

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "user@example.com"
    assert "plan_tier" not in body
    assert "feature_flags" not in body


def test_patch_me_updates_profile_email_and_password(api_client):
    register_user(api_client)
    login = login_user(api_client)
    token = login.json()["access_token"]

    response = api_client.patch(
        "/api/v1/auth/me",
        json={
            "full_name": "Updated User",
            "email": "updated@example.com",
            "current_password": "testpass123",
            "new_password": "newpass123",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["full_name"] == "Updated User"
    assert body["email"] == "updated@example.com"

    old_login = login_user(api_client, email="updated@example.com", password="testpass123")
    new_login = login_user(api_client, email="updated@example.com", password="newpass123")
    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_patch_me_requires_both_password_fields(api_client):
    register_user(api_client)
    token = login_user(api_client).json()["access_token"]

    response = api_client.patch(
        "/api/v1/auth/me",
        json={"new_password": "newpass123"},
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "password_change_requires_both_fields"


def test_patch_me_rejects_incorrect_current_password(api_client):
    register_user(api_client)
    token = login_user(api_client).json()["access_token"]

    response = api_client.patch(
        "/api/v1/auth/me",
        json={
            "current_password": "wrongpass123",
            "new_password": "newpass123",
        },
        headers=auth_headers(token),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "current_password_incorrect"


def test_e2e_reset_workspace_requires_configuration(api_client):
    api_client.app.dependency_overrides[dependency_module.get_app_settings] = lambda: Settings(
        e2e_test_user_email=""
    )
    try:
        register_user(api_client, email="tests@ragdoll.local")
        token = login_user(api_client, email="tests@ragdoll.local").json()["access_token"]

        response = api_client.post("/api/v1/auth/e2e/reset-workspace", headers=auth_headers(token))

        assert response.status_code == 404
        assert response.json()["code"] == "e2e_test_user_reset_not_enabled"
    finally:
        api_client.app.dependency_overrides.clear()


def test_e2e_reset_workspace_rejects_non_configured_user(api_client):
    api_client.app.dependency_overrides[dependency_module.get_app_settings] = lambda: Settings(
        e2e_test_user_email="tests@ragdoll.local"
    )
    try:
        register_user(api_client, email="other@example.com")
        token = login_user(api_client, email="other@example.com").json()["access_token"]

        response = api_client.post("/api/v1/auth/e2e/reset-workspace", headers=auth_headers(token))

        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"
    finally:
        api_client.app.dependency_overrides.clear()


def test_e2e_reset_workspace_cleans_shared_user_state(api_client, db_session):
    storage = InMemoryDocumentStorage()
    vector_cleanup = InMemoryVectorCleanupService()
    graph_cleanup = InMemoryGraphCleanupService()
    api_client.app.dependency_overrides[dependency_module.get_app_settings] = lambda: Settings(
        e2e_test_user_email="tests@ragdoll.local"
    )
    api_client.app.dependency_overrides[dependency_module.get_document_storage_service] = lambda: storage
    api_client.app.dependency_overrides[dependency_module.get_vector_cleanup] = lambda: vector_cleanup
    api_client.app.dependency_overrides[dependency_module.get_graph_cleanup] = lambda: graph_cleanup

    try:
        register_user(api_client, email="tests@ragdoll.local")
        token = login_user(api_client, email="tests@ragdoll.local").json()["access_token"]
        user = db_session.query(User).filter(User.email == "tests@ragdoll.local").one()
        default_space = (
            db_session.query(Space).filter(Space.owner_user_id == user.id, Space.is_default.is_(True)).one()
        )
        extra_space = Space(owner_user_id=user.id, name="Extra Space", description="To be removed", is_default=False)
        db_session.add(extra_space)
        db_session.flush()

        document = Document(
            space_id=default_space.id,
            uploaded_by=user.id,
            title="Shared test doc",
            original_filename="shared-test.txt",
            mime_type="text/plain",
            file_type="txt",
            file_size=18,
            storage_key="originals/tests/shared-test.txt",
            source_kind="manual_upload",
            processing_status={
                "overall": "completed",
                "upload": "completed",
                "parsing": "completed",
                "vector": "completed",
                "extraction": "completed",
                "graph": "completed",
                "detail": None,
            },
            preview_text="shared test",
            original_text_content="shared test"
        )
        db_session.add(document)
        db_session.flush()
        document_id = document.id
        storage.seed_original_file(document.storage_key, b"shared test content")
        storage.derived_prefixes.add(f"derived/{document_id}")

        db_session.add(
            CorrectionRecord(
                space_id=default_space.id,
                submitted_by=user.id,
                document_id=document.id,
                proposed_value="Updated shared value",
                rationale="Cleanup should remove this row.",
                status="pending",
            )
        )
        db_session.add(
            UsageEvent(
                user_id=user.id,
                event_type="document_uploaded",
                quantity=1,
                document_id=document.id,
                space_id=default_space.id,
            )
        )
        db_session.add(
            UserUsageSnapshot(
                user_id=user.id,
                document_count=1,
                chunk_count=4,
                storage_bytes=18,
                tokens_5h=0,
                tokens_week=0,
            )
        )
        db_session.commit()

        response = api_client.post("/api/v1/auth/e2e/reset-workspace", headers=auth_headers(token))

        assert response.status_code == 200, response.text
        assert response.json()["success"] is True

        db_session.expire_all()
        spaces = db_session.query(Space).filter(Space.owner_user_id == user.id).all()
        assert len(spaces) == 1
        assert spaces[0].is_default is True
        assert spaces[0].archived_at is None
        assert db_session.query(Document).filter(Document.uploaded_by == user.id).count() == 0
        assert db_session.query(CorrectionRecord).filter(CorrectionRecord.submitted_by == user.id).count() == 0
        assert db_session.query(UsageEvent).filter(UsageEvent.user_id == user.id).count() == 0
        assert db_session.get(UserUsageSnapshot, user.id) is None
        assert storage.originals == {}
        assert f"derived/{document_id}" not in storage.derived_prefixes
        assert vector_cleanup.cleaned_document_ids == {document_id}
        assert graph_cleanup.cleaned_document_ids == {document_id}
    finally:
        api_client.app.dependency_overrides.clear()
