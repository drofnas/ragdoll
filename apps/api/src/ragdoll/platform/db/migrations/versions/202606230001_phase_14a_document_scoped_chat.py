"""phase_14a_document_scoped_chat

Revision ID: 202606230001
Revises: 202606220003
Create Date: 2026-06-23 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606230001"
down_revision = "202606220003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("chat_sessions") as batch_op:
        batch_op.add_column(sa.Column("document_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_chat_sessions_document_id_documents",
            "documents",
            ["document_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_chat_sessions_document_id", ["document_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("chat_sessions") as batch_op:
        batch_op.drop_index("ix_chat_sessions_document_id")
        batch_op.drop_constraint("fk_chat_sessions_document_id_documents", type_="foreignkey")
        batch_op.drop_column("document_id")
