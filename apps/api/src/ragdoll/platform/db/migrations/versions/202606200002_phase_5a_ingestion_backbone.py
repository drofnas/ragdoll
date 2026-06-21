"""phase_5a_ingestion_backbone

Revision ID: 202606200002
Revises: 202606200001
Create Date: 2026-06-20 00:02:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606200002"
down_revision = "202606200001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("text_preview", sa.Text(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="ux_document_chunks_document_chunk_index"),
    )
    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"], unique=False)
    op.create_index("ix_document_chunks_space_id", "document_chunks", ["space_id"], unique=False)

    op.create_table(
        "document_processing_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("requested_stage", sa.String(length=32), nullable=False, server_default="parsing"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("visible_error_detail", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_document_processing_jobs_status_queued_at",
        "document_processing_jobs",
        ["status", "queued_at"],
        unique=False,
    )
    op.create_index("ix_document_processing_jobs_document_id", "document_processing_jobs", ["document_id"], unique=False)
    op.create_index("ix_document_processing_jobs_uploaded_by", "document_processing_jobs", ["uploaded_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_document_processing_jobs_uploaded_by", table_name="document_processing_jobs")
    op.drop_index("ix_document_processing_jobs_document_id", table_name="document_processing_jobs")
    op.drop_index("ix_document_processing_jobs_status_queued_at", table_name="document_processing_jobs")
    op.drop_table("document_processing_jobs")
    op.drop_index("ix_document_chunks_space_id", table_name="document_chunks")
    op.drop_index("ix_document_chunks_document_id", table_name="document_chunks")
    op.drop_table("document_chunks")
