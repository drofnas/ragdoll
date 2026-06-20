from __future__ import annotations

from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError
from ragdoll.core.security import get_password_hash, verify_password
from ragdoll.modules.users.api.schemas import UpdateCurrentUserRequest
from ragdoll.modules.users.infrastructure.repository import UsersRepository
from ragdoll.platform.db.models import User


def update_current_user(session: Session, user: User, payload: UpdateCurrentUserRequest) -> User:
    repo = UsersRepository(session)

    if payload.new_password is not None or payload.current_password is not None:
        if not payload.current_password or not payload.new_password:
            raise ApplicationError(
                "Both current_password and new_password are required to change password.",
                status_code=400,
                title="Bad request",
                type_uri="https://ragdoll.dev/problems/bad-request",
                code="password_change_requires_both_fields",
            )
        if not verify_password(payload.current_password, user.hashed_password):
            raise ApplicationError(
                "Current password is incorrect.",
                status_code=400,
                title="Bad request",
                type_uri="https://ragdoll.dev/problems/bad-request",
                code="current_password_incorrect",
            )
        user.hashed_password = get_password_hash(payload.new_password)
        user.must_change_password = False

    if payload.full_name is not None:
        user.full_name = payload.full_name

    if payload.email is not None and payload.email != user.email:
        existing = repo.get_by_email(payload.email)
        if existing is not None and existing.id != user.id:
            raise ApplicationError(
                "Email already registered.",
                status_code=409,
                title="Conflict",
                type_uri="https://ragdoll.dev/problems/conflict",
                code="email_already_registered",
            )
        user.email = payload.email

    session.commit()
    session.refresh(user)
    return user
