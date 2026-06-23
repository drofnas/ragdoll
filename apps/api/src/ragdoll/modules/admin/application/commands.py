from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError
from ragdoll.modules.admin.api.schemas import AdminUpdateUserRequest
from ragdoll.modules.users.infrastructure.repository import UsersRepository
from ragdoll.platform.db.models import User


def update_managed_user(session: Session, user_id: UUID, payload: AdminUpdateUserRequest) -> User:
    repo = UsersRepository(session)
    user = repo.get_by_id(user_id)
    if user is None:
        raise ApplicationError(
            "The requested user was not found.",
            status_code=404,
            title="Not found",
            type_uri="https://ragdoll.dev/problems/not-found",
            code="user_not_found",
        )

    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.is_admin is not None:
        user.is_admin = payload.is_admin
    if payload.must_change_password is not None:
        user.must_change_password = payload.must_change_password

    session.commit()
    session.refresh(user)
    return user
