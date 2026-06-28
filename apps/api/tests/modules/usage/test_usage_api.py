from __future__ import annotations

from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from ragdoll.platform.db.models import Document, Space, UsageEvent, User
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
    file_size: int,
    chunk_count: int,
    overall: str,
) -> Document:
    payload = default_processing_status_payload()
    payload["overall"] = overall
    document = Document(
        space_id=space.id,
        uploaded_by=uploader.id,
        title=f"{overall}-{file_size}.txt",
        original_filename=f"{overall}-{file_size}.txt",
        mime_type="text/plain",
        file_type="txt",
        file_size=file_size,
        storage_key=f"documents/{overall}-{file_size}.txt",
        source_kind="manual_upload",
        processing_status=payload,
        chunk_count=chunk_count,
        indexed_chunk_count=chunk_count if overall == "completed" else max(1, chunk_count - 1),
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def test_usage_route_requires_authentication(api_client):
    response = api_client.get("/api/v1/usage/me")
    assert response.status_code == 401


def test_usage_summary_reports_document_totals_and_percentages(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    register_and_login(api_client, email="other@example.com")

    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    other = db_session.query(User).filter(User.email == "other@example.com").one()
    _seed_document(
        db_session,
        space=_default_space(db_session, owner),
        uploader=owner,
        file_size=100,
        chunk_count=3,
        overall="completed",
    )
    _seed_document(
        db_session,
        space=_default_space(db_session, owner),
        uploader=owner,
        file_size=250,
        chunk_count=7,
        overall="pending",
    )
    _seed_document(
        db_session,
        space=_default_space(db_session, other),
        uploader=other,
        file_size=999,
        chunk_count=99,
        overall="completed",
    )

    response = api_client.get("/api/v1/usage/me", headers=auth_headers(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["usage"]["documents"] == 2
    assert body["usage"]["chunks"] == 10
    assert body["usage"]["storage_bytes"] == 350
    assert body["limits"]["documents"] is None
    assert body["percent_used"]["documents"] is None
    assert body["limits"]["max_file_size_bytes"] == 100 * 1024 * 1024
    assert body["status"]["partially_indexed_documents"] == 1
    assert body["status"]["upload_blocked"] is False


def test_usage_summary_updates_after_soft_delete(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    document = _seed_document(
        db_session,
        space=_default_space(db_session, owner),
        uploader=owner,
        file_size=500,
        chunk_count=5,
        overall="completed",
    )

    first = api_client.get("/api/v1/usage/me", headers=auth_headers(token))
    assert first.status_code == 200
    assert first.json()["usage"]["documents"] == 1

    document.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    second = api_client.get("/api/v1/usage/me", headers=auth_headers(token))
    assert second.status_code == 200
    assert second.json()["usage"]["documents"] == 0
    assert second.json()["usage"]["storage_bytes"] == 0


def test_usage_summary_reports_token_windows_and_reset_times(api_client, db_session):
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            UsageEvent(
                user_id=owner.id,
                event_type="chat_tokens",
                quantity=120,
                occurred_at=now - timedelta(hours=2),
                space_id=_default_space(db_session, owner).id,
            ),
            UsageEvent(
                user_id=owner.id,
                event_type="chat_tokens",
                quantity=250,
                occurred_at=now - timedelta(days=2),
                space_id=_default_space(db_session, owner).id,
            ),
            UsageEvent(
                user_id=owner.id,
                event_type="chat_tokens",
                quantity=1000,
                occurred_at=now - timedelta(days=8),
                space_id=_default_space(db_session, owner).id,
            ),
        ]
    )
    db_session.commit()

    response = api_client.get("/api/v1/usage/me", headers=auth_headers(token))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["usage"]["tokens_5h"] == 120
    assert body["usage"]["tokens_week"] == 370
    assert body["resets_at"]["tokens_5h_resets_at"] is not None
    assert body["resets_at"]["tokens_week_resets_at"] is not None
