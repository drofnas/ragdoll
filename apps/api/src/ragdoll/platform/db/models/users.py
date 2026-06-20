from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy import Uuid as SqlUuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ragdoll.platform.db.models_base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Canonical user record for authentication and plan ownership."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(default=False, nullable=False)
    plan_tier: Mapped[str] = mapped_column(String(32), default="free", nullable=False)
    feature_flag_overrides: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        server_default=func.now(),
    )

    spaces: Mapped[list["Space"]] = relationship(
        back_populates="owner",
        cascade="all, delete-orphan",
    )
