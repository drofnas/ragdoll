from __future__ import annotations

from urllib.parse import parse_qs

from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError, AuthenticationRequiredError
from ragdoll.core.security import create_access_token, get_password_hash, verify_password
from ragdoll.modules.auth.api.schemas import LoginTokenResponse, RegisterRequest
from ragdoll.modules.spaces.application.commands import create_default_space_for_user
from ragdoll.modules.users.application.queries import build_user_profile_response
from ragdoll.modules.users.infrastructure.repository import UsersRepository
from ragdoll.platform.db.models import User


def register_user(session: Session, payload: RegisterRequest) -> User:
    """Register a new user and create the default Space in one transaction."""
    users_repo = UsersRepository(session)
    if users_repo.get_by_email(payload.email) is not None:
        raise ApplicationError(
            "Email already registered.",
            status_code=409,
            title="Conflict",
            type_uri="https://ragdoll.dev/problems/conflict",
            code="email_already_registered",
        )

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
    )
    users_repo.add(user)
    session.flush()
    create_default_space_for_user(session, user.id)
    session.commit()
    session.refresh(user)
    return user


def login_user(session: Session, username: str, password: str) -> LoginTokenResponse:
    """Authenticate a user and return the bearer token payload."""
    users_repo = UsersRepository(session)
    user = users_repo.get_by_email(username)
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationRequiredError("Incorrect username or password.")

    users_repo.record_login(user)
    session.commit()
    return LoginTokenResponse(
        access_token=create_access_token({"sub": str(user.id), "email": user.email}),
        token_type="bearer",
        must_change_password=user.must_change_password,
    )


def parse_oauth_password_form(raw_body: bytes) -> tuple[str, str]:
    """Parse the legacy OAuth2 password form without python-multipart."""
    values = parse_qs(raw_body.decode("utf-8"), keep_blank_values=False)
    username = (values.get("username") or [""])[0].strip().lower()
    password = (values.get("password") or [""])[0]
    if not username or not password:
        raise ApplicationError(
            "The request payload or parameters did not match the expected schema.",
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        )
    return username, password


def build_registration_response(user: User):
    return build_user_profile_response(user)
