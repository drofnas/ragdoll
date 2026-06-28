from __future__ import annotations

from urllib.parse import urlencode

from ragdoll.platform.db.models import User


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
