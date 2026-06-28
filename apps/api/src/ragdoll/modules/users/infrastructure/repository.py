from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ragdoll.modules.users.domain.policies import normalize_email_address
from ragdoll.platform.db.models import User


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UsersRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, user: User) -> None:
        self.session.add(user)

    def get_by_id(self, user_id: UUID) -> User | None:
        stmt = select(User).where(User.id == user_id)
        return self.session.scalar(stmt)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == normalize_email_address(email))
        return self.session.scalar(stmt)

    def list_paginated(self, *, limit: int, offset: int) -> tuple[list[User], int]:
        items = list(
            self.session.scalars(
                select(User).order_by(User.created_at.desc(), User.email.asc()).limit(limit).offset(offset)
            )
        )
        total = self.session.scalar(select(func.count()).select_from(User)) or 0
        return items, int(total)

    def record_login(self, user: User) -> None:
        user.last_login = utc_now()
