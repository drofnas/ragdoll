from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from uuid import UUID, uuid4, uuid5

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func, text
from sqlalchemy import Uuid as SqlUuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ragdoll.platform.db.models_base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def default_processing_status_payload() -> dict[str, str | None]:
    return {
        "overall": "pending",
        "upload": "completed",
        "parsing": "pending",
        "vector": "pending",
        "extraction": "pending",
        "graph": "pending",
        "detail": None,
    }


def stable_document_chunk_id(*, document_id: UUID, chunk_index: int, checksum: str) -> UUID:
    return uuid5(document_id, f"{chunk_index}:{checksum}")


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
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentChunk.chunk_index",
    )
    processing_jobs: Mapped[list["DocumentProcessingJob"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentProcessingJob.queued_at.desc()",
    )
    vectors: Mapped[list["DocumentChunkVector"]] = relationship(cascade="all, delete-orphan")
    entities: Mapped[list["Entity"]] = relationship(cascade="all, delete-orphan")
    graph_edges: Mapped[list["GraphEdge"]] = relationship(cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Stable relational chunk projection for later retrieval and citations."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="ux_document_chunks_document_chunk_index"),
        Index("ix_document_chunks_document_id", "document_id"),
        Index("ix_document_chunks_space_id", "space_id"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    text_preview: Mapped[str] = mapped_column(Text, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
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

    document: Mapped["Document"] = relationship(back_populates="chunks")
    vectors: Mapped[list["DocumentChunkVector"]] = relationship(cascade="all, delete-orphan")
    entities: Mapped[list["Entity"]] = relationship(cascade="all, delete-orphan")
    graph_edges: Mapped[list["GraphEdge"]] = relationship(cascade="all, delete-orphan")

    @classmethod
    def from_text(
        cls,
        *,
        document_id: UUID,
        space_id: UUID,
        chunk_index: int,
        text_content: str,
        start_line: int = 1,
    ) -> "DocumentChunk":
        checksum = sha256(text_content.encode("utf-8")).hexdigest()
        return cls(
            id=stable_document_chunk_id(document_id=document_id, chunk_index=chunk_index, checksum=checksum),
            document_id=document_id,
            space_id=space_id,
            chunk_index=chunk_index,
            start_line=start_line,
            text_content=text_content,
            text_preview=text_content[:280],
            checksum=checksum,
        )


class DocumentProcessingJob(Base):
    """Queued background parsing work owned by the relational store."""

    __tablename__ = "document_processing_jobs"
    __table_args__ = (
        Index("ix_document_processing_jobs_status_queued_at", "status", "queued_at"),
        Index("ix_document_processing_jobs_document_id", "document_id"),
        Index("ix_document_processing_jobs_uploaded_by", "uploaded_by"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    document_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
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
    requested_stage: Mapped[str] = mapped_column(String(32), nullable=False, default="parsing")
    job_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="upload")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    cleanup_derived_artifacts: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=text("false"))
    reset_document_content: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=text("false"))
    clear_existing_chunks: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=text("false"))
    clear_existing_entities: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=text("false"))
    cleanup_vectors: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=text("false"))
    cleanup_graph: Mapped[bool] = mapped_column(nullable=False, default=False, server_default=text("false"))
    visible_error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        server_default=func.now(),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped["Document"] = relationship(back_populates="processing_jobs")
