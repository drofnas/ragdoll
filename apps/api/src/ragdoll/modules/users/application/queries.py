from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.core.auth import AuthenticatedPrincipal
from ragdoll.core.exceptions import AuthenticationRequiredError
from ragdoll.modules.users.api.schemas import UserProfileResponse
from ragdoll.modules.users.domain.policies import normalize_email_address
from ragdoll.modules.users.infrastructure.repository import UsersRepository
from ragdoll.platform.db.models import User


def build_user_profile_response(user: User) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        must_change_password=user.must_change_password,
        last_login=user.last_login,
    )


def build_authenticated_principal(user: User) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        subject=str(user.id),
        email=user.email,
        is_admin=user.is_admin,
    )


def get_user_by_subject(session: Session, subject: str) -> User:
    try:
        user_id = UUID(subject)
    except ValueError as exc:
        raise AuthenticationRequiredError("Authentication token subject is invalid.") from exc

    repo = UsersRepository(session)
    user = repo.get_by_id(user_id)
    if user is None:
        raise AuthenticationRequiredError("Authenticated user was not found.")
    return user


def get_user_by_email(session: Session, email: str) -> User | None:
    return UsersRepository(session).get_by_email(normalize_email_address(email))
