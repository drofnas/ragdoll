from __future__ import annotations

from uuid import UUID

from ragdoll.modules.admin.api.schemas import AdminEffectiveLimitsResponse
from ragdoll.platform.db.models import User


def register_and_login(api_client, *, email: str = "admin@example.com", password: str = "testpass123") -> str:
    register = api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Admin User"},
    )
    assert register.status_code == 201, register.text
    login = api_client.post(
        "/api/v1/auth/login",
        content=f"username={email}&password={password}",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_admin_routes_require_admin_access(api_client, db_session):
    token = register_and_login(api_client, email="user@example.com")
    user = db_session.query(User).filter(User.email == "user@example.com").one()

    responses = [
        api_client.get("/api/v1/admin/users", headers=auth_headers(token)),
        api_client.get(f"/api/v1/admin/users/{user.id}", headers=auth_headers(token)),
        api_client.patch(f"/api/v1/admin/users/{user.id}", headers=auth_headers(token), json={"is_active": False}),
        api_client.get("/api/v1/admin/effective-limits", headers=auth_headers(token)),
    ]

    assert all(response.status_code == 403 for response in responses)


def test_admin_can_list_and_update_users(api_client, db_session):
    token = register_and_login(api_client, email="admin@example.com")
    admin = db_session.query(User).filter(User.email == "admin@example.com").one()
    admin.is_admin = True
    db_session.commit()

    register_and_login(api_client, email="member@example.com")
    member = db_session.query(User).filter(User.email == "member@example.com").one()

    listing = api_client.get("/api/v1/admin/users", headers=auth_headers(token))
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["total"] >= 2
    assert any(item["email"] == "member@example.com" for item in body["items"])

    detail = api_client.get(f"/api/v1/admin/users/{member.id}", headers=auth_headers(token))
    assert detail.status_code == 200, detail.text
    assert detail.json()["email"] == "member@example.com"

    patch = api_client.patch(
        f"/api/v1/admin/users/{member.id}",
        headers=auth_headers(token),
        json={"is_admin": True, "must_change_password": True},
    )
    assert patch.status_code == 200, patch.text
    updated = patch.json()
    assert updated["is_admin"] is True
    assert updated["must_change_password"] is True


def test_admin_effective_limits_reflect_instance_policy(api_client, db_session):
    token = register_and_login(api_client, email="admin@example.com")
    admin = db_session.query(User).filter(User.email == "admin@example.com").one()
    admin.is_admin = True
    db_session.commit()

    response = api_client.get("/api/v1/admin/effective-limits", headers=auth_headers(token))
    assert response.status_code == 200, response.text
    body = AdminEffectiveLimitsResponse.model_validate(response.json())
    assert body.documents is None
    assert body.max_file_size_bytes == 100 * 1024 * 1024
    assert body.upload_rate_limit.enabled is True
