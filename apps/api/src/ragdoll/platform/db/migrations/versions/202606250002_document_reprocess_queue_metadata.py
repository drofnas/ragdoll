"""document_reprocess_queue_metadata

Revision ID: 202606250002
Revises: 202606250001
Create Date: 2026-06-25 00:02:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606250002"
down_revision = "202606250001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_processing_jobs",
        sa.Column("job_kind", sa.String(length=32), nullable=False, server_default="upload"),
    )
    op.add_column(
        "document_processing_jobs",
        sa.Column("cleanup_derived_artifacts", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "document_processing_jobs",
        sa.Column("reset_document_content", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "document_processing_jobs",
        sa.Column("clear_existing_chunks", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "document_processing_jobs",
        sa.Column("clear_existing_entities", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "document_processing_jobs",
        sa.Column("cleanup_vectors", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "document_processing_jobs",
        sa.Column("cleanup_graph", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("document_processing_jobs", "cleanup_graph")
    op.drop_column("document_processing_jobs", "cleanup_vectors")
    op.drop_column("document_processing_jobs", "clear_existing_entities")
    op.drop_column("document_processing_jobs", "clear_existing_chunks")
    op.drop_column("document_processing_jobs", "reset_document_content")
    op.drop_column("document_processing_jobs", "cleanup_derived_artifacts")
    op.drop_column("document_processing_jobs", "job_kind")
