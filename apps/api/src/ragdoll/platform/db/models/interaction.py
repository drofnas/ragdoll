from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, JSON, String, Text, UniqueConstraint, func, text
from sqlalchemy import Uuid as SqlUuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ragdoll.platform.db.models_base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChatSession(Base):
    """Persisted chat session scoped to one Space owner."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_document_id", "document_id"),
        Index("ix_chat_sessions_space_id", "space_id"),
        Index("ix_chat_sessions_owner_user_id", "owner_user_id"),
        Index("ix_chat_sessions_updated_at", "updated_at"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New chat")
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

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at.asc()",
    )


class ChatMessage(Base):
    """Persisted user or assistant message."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        Index("ix_chat_messages_session_id", "session_id"),
        Index("ix_chat_messages_space_id", "space_id"),
        Index("ix_chat_messages_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_user_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    suggestions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    evidence: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    retrieval_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)
    degraded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
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

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class PinnedFact(Base):
    """Space-scoped pinned fact with its current evidence-backed value."""

    __tablename__ = "pinned_facts"
    __table_args__ = (
        UniqueConstraint("space_id", "key", name="ux_pinned_facts_space_key"),
        Index("ix_pinned_facts_space_id", "space_id"),
        Index("ix_pinned_facts_owner_user_id", "owner_user_id"),
        Index("ix_pinned_facts_is_active", "is_active"),
        Index("ix_pinned_facts_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    owner_user_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    entity_type_hint: Mapped[str | None] = mapped_column(String(80), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    value_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown", server_default="unknown")
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_document_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    evidence: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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


class PinnedFactCandidate(Base):
    """Detected or submitted candidate update for one pinned fact."""

    __tablename__ = "pinned_fact_candidates"
    __table_args__ = (
        Index("ix_pinned_fact_candidates_pinned_fact_id", "pinned_fact_id"),
        Index("ix_pinned_fact_candidates_space_id", "space_id"),
        Index("ix_pinned_fact_candidates_source_document_id", "source_document_id"),
        Index("ix_pinned_fact_candidates_status", "status"),
        UniqueConstraint("pinned_fact_id", "idempotency_key", name="ux_pinned_fact_candidates_fact_idempotency"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    pinned_fact_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("pinned_facts.id", ondelete="CASCADE"),
        nullable=False,
    )
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_document_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    proposed_value_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    proposed_value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    change_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        server_default=func.now(),
    )


class PinnedFactHistory(Base):
    """Append-only change log for pinned fact versions and restores."""

    __tablename__ = "pinned_fact_history"
    __table_args__ = (
        Index("ix_pinned_fact_history_pinned_fact_id", "pinned_fact_id"),
        Index("ix_pinned_fact_history_space_id", "space_id"),
        Index("ix_pinned_fact_history_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    pinned_fact_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("pinned_facts.id", ondelete="CASCADE"),
        nullable=False,
    )
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("pinned_fact_candidates.id", ondelete="SET NULL"),
        nullable=True,
    )
    restored_from_history_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("pinned_fact_history.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="system", server_default="system")
    reason: Mapped[str] = mapped_column(String(64), nullable=False)
    old_value_kind: Mapped[str | None] = mapped_column(String(16), nullable=True)
    old_value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    old_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_value_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    new_value_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    old_evidence: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    new_evidence: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    update_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        server_default=func.now(),
    )


class ChangeEvent(Base):
    """Append-only change event visible in the changes feed."""

    __tablename__ = "change_events"
    __table_args__ = (
        Index("ix_change_events_space_id", "space_id"),
        Index("ix_change_events_event_type", "event_type"),
        Index("ix_change_events_created_at", "created_at"),
        Index("ix_change_events_document_id", "document_id"),
        Index("ix_change_events_pinned_fact_id", "pinned_fact_id"),
        Index("ix_change_events_correction_id", "correction_id"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    actor_user_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    pinned_fact_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("pinned_facts.id", ondelete="SET NULL"),
        nullable=True,
    )
    correction_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("correction_records.id", ondelete="SET NULL"),
        nullable=True,
    )
    chat_session_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        server_default=func.now(),
    )


class ChangeEventRead(Base):
    """Per-user read marker for one change event."""

    __tablename__ = "change_event_reads"
    __table_args__ = (
        UniqueConstraint("change_event_id", "user_id", name="ux_change_event_reads_event_user"),
        Index("ix_change_event_reads_user_id", "user_id"),
        Index("ix_change_event_reads_change_event_id", "change_event_id"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    change_event_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("change_events.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        server_default=func.now(),
    )


class CorrectionRecord(Base):
    """User-submitted correction or verification record."""

    __tablename__ = "correction_records"
    __table_args__ = (
        Index("ix_correction_records_space_id", "space_id"),
        Index("ix_correction_records_status", "status"),
        Index("ix_correction_records_pinned_fact_id", "pinned_fact_id"),
        Index("ix_correction_records_document_id", "document_id"),
        Index("ix_correction_records_entity_id", "entity_id"),
        Index("ix_correction_records_chat_session_id", "chat_session_id"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    submitted_by: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    chat_session_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("chat_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    chat_message_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("chat_messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    pinned_fact_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("pinned_facts.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    entity_id: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("canonical_entities.id", ondelete="SET NULL"),
        nullable=True,
    )
    locator_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_value: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[UUID | None] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
