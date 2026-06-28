"""document_chunk_start_line

Revision ID: 202606240001
Revises: 202606230001
Create Date: 2026-06-24 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606240001"
down_revision = "202606230001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column("start_line", sa.Integer(), nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("document_chunks", "start_line")
