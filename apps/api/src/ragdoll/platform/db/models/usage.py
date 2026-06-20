from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, JSON, String
from sqlalchemy import Uuid as SqlUuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ragdoll.platform.db.models_base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UsageEvent(Base):
    """Append-only usage event ledger for later quota features."""

    __tablename__ = "usage_events"
    __table_args__ = (
        Index("ix_usage_events_user_id", "user_id"),
        Index("ix_usage_events_event_type", "event_type"),
        Index("ix_usage_events_occurred_at", "occurred_at"),
        Index("ix_usage_events_document_id", "document_id"),
        Index("ix_usage_events_space_id", "space_id"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    quantity: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )
    document_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    space_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    user: Mapped["User"] = relationship(back_populates="usage_events")
    document: Mapped["Document | None"] = relationship(back_populates="usage_events")


class UserUsageSnapshot(Base):
    """Cached usage totals for account-facing summary reads."""

    __tablename__ = "user_usage_snapshots"

    user_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    document_count: Mapped[int] = mapped_column(nullable=False, default=0)
    chunk_count: Mapped[int] = mapped_column(nullable=False, default=0)
    storage_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tokens_5h: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tokens_week: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
    )

    user: Mapped["User"] = relationship(back_populates="usage_snapshot")
