"""phase_3a_documents_and_usage

Revision ID: 202606200001
Revises: 202606190001
Create Date: 2026-06-20 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606200001"
down_revision = "202606190001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("mime_type", sa.String(length=255), nullable=False),
        sa.Column("file_type", sa.String(length=32), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("source_kind", sa.String(length=32), nullable=False, server_default="manual_upload"),
        sa.Column("source_label", sa.String(length=500), nullable=True),
        sa.Column("preview_text", sa.Text(), nullable=True),
        sa.Column("original_text_content", sa.Text(), nullable=True),
        sa.Column("processing_status", sa.JSON(), nullable=False),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("indexed_chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_documents_space_id", "documents", ["space_id"], unique=False)
    op.create_index("ix_documents_uploaded_by", "documents", ["uploaded_by"], unique=False)
    op.create_index("ix_documents_uploaded_at", "documents", ["created_at"], unique=False)
    op.create_index("ix_documents_file_type", "documents", ["file_type"], unique=False)
    op.create_index("ix_documents_deleted_at", "documents", ["deleted_at"], unique=False)
    op.create_index(
        "ix_documents_active_space_uploaded_at",
        "documents",
        ["space_id", "created_at"],
        unique=False,
        postgresql_where=sa.text("deleted_at IS NULL"),
        sqlite_where=sa.text("deleted_at IS NULL"),
    )

    op.create_table(
        "usage_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("space_id", sa.Uuid(), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_events_user_id", "usage_events", ["user_id"], unique=False)
    op.create_index("ix_usage_events_event_type", "usage_events", ["event_type"], unique=False)
    op.create_index("ix_usage_events_occurred_at", "usage_events", ["occurred_at"], unique=False)
    op.create_index("ix_usage_events_document_id", "usage_events", ["document_id"], unique=False)
    op.create_index("ix_usage_events_space_id", "usage_events", ["space_id"], unique=False)

    op.create_table(
        "user_usage_snapshots",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("document_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("storage_bytes", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tokens_5h", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("tokens_week", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_usage_snapshots")
    op.drop_index("ix_usage_events_space_id", table_name="usage_events")
    op.drop_index("ix_usage_events_document_id", table_name="usage_events")
    op.drop_index("ix_usage_events_occurred_at", table_name="usage_events")
    op.drop_index("ix_usage_events_event_type", table_name="usage_events")
    op.drop_index("ix_usage_events_user_id", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_index("ix_documents_active_space_uploaded_at", table_name="documents")
    op.drop_index("ix_documents_deleted_at", table_name="documents")
    op.drop_index("ix_documents_file_type", table_name="documents")
    op.drop_index("ix_documents_uploaded_at", table_name="documents")
    op.drop_index("ix_documents_uploaded_by", table_name="documents")
    op.drop_index("ix_documents_space_id", table_name="documents")
    op.drop_table("documents")
