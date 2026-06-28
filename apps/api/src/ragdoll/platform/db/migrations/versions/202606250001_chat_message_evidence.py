"""chat_message_evidence

Revision ID: 202606250001
Revises: 202606240001
Create Date: 2026-06-25 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606250001"
down_revision = "202606240001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chat_messages", sa.Column("evidence", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("chat_messages", "evidence")
