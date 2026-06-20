from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import AuthenticationRequiredError


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def get_password_hash(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def create_access_token(
    data: dict[str, Any],
    *,
    expires_delta: timedelta | None = None,
    settings: Settings | None = None,
) -> str:
    runtime_settings = settings or get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=runtime_settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(
        to_encode,
        runtime_settings.secret_key,
        algorithm=runtime_settings.algorithm,
    )


def decode_access_token(token: str, *, settings: Settings | None = None) -> dict[str, Any]:
    runtime_settings = settings or get_settings()
    try:
        return jwt.decode(
            token,
            runtime_settings.secret_key,
            algorithms=[runtime_settings.algorithm],
        )
    except JWTError as exc:
        raise AuthenticationRequiredError("Authentication token is invalid or expired.") from exc
