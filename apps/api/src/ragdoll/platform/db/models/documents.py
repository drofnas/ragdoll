from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text, func, text
from sqlalchemy import Uuid as SqlUuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ragdoll.platform.db.models_base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def default_processing_status_payload() -> dict[str, str | None]:
    return {
        "overall": "pending",
        "upload": "pending",
        "parsing": "pending",
        "vector": "pending",
        "extraction": "pending",
        "graph": "pending",
        "detail": None,
    }


class Document(Base):
    """Document metadata row owned by the relational store."""

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_space_id", "space_id"),
        Index("ix_documents_uploaded_by", "uploaded_by"),
        Index("ix_documents_uploaded_at", "created_at"),
        Index("ix_documents_file_type", "file_type"),
        Index("ix_documents_deleted_at", "deleted_at"),
        Index(
            "ix_documents_active_space_uploaded_at",
            "space_id",
            "created_at",
            postgresql_where=text("deleted_at IS NULL"),
            sqlite_where=text("deleted_at IS NULL"),
        ),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    uploaded_by: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)
    file_size: Mapped[int] = mapped_column(nullable=False, default=0)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    source_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="manual_upload")
    source_label: Mapped[str | None] = mapped_column(String(500), nullable=True)
    preview_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_status: Mapped[dict[str, str | None]] = mapped_column(
        JSON,
        nullable=False,
        default=default_processing_status_payload,
    )
    chunk_count: Mapped[int] = mapped_column(nullable=False, default=0)
    indexed_chunk_count: Mapped[int] = mapped_column(nullable=False, default=0)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    space: Mapped["Space"] = relationship(back_populates="documents")
    uploader: Mapped["User"] = relationship(back_populates="uploaded_documents")
    usage_events: Mapped[list["UsageEvent"]] = relationship(back_populates="document")

