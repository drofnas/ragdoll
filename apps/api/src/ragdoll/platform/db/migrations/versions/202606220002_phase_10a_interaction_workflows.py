"""phase_10a_interaction_workflows

Revision ID: 202606220002
Revises: 202606220001
Create Date: 2026-06-22 00:02:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606220002"
down_revision = "202606220001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False, server_default="New chat"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_sessions_space_id", "chat_sessions", ["space_id"], unique=False)
    op.create_index("ix_chat_sessions_owner_user_id", "chat_sessions", ["owner_user_id"], unique=False)
    op.create_index("ix_chat_sessions_updated_at", "chat_sessions", ["updated_at"], unique=False)

    op.create_table(
        "tracked_fields",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("owner_user_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("entity_type_hint", sa.String(length=80), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("space_id", "key", name="ux_tracked_fields_space_key"),
    )
    op.create_index("ix_tracked_fields_space_id", "tracked_fields", ["space_id"], unique=False)
    op.create_index("ix_tracked_fields_owner_user_id", "tracked_fields", ["owner_user_id"], unique=False)
    op.create_index("ix_tracked_fields_is_active", "tracked_fields", ["is_active"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Uuid(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("suggestions", sa.JSON(), nullable=True),
        sa.Column("retrieval_mode", sa.String(length=32), nullable=True),
        sa.Column("degraded", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["author_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["chat_sessions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"], unique=False)
    op.create_index("ix_chat_messages_space_id", "chat_messages", ["space_id"], unique=False)
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"], unique=False)

    op.create_table(
        "correction_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by", sa.Uuid(), nullable=False),
        sa.Column("chat_session_id", sa.Uuid(), nullable=True),
        sa.Column("chat_message_id", sa.Uuid(), nullable=True),
        sa.Column("tracked_field_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("locator_text", sa.Text(), nullable=True),
        sa.Column("proposed_value", sa.Text(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["chat_message_id"], ["chat_messages.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chat_session_id"], ["chat_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["entity_id"], ["canonical_entities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tracked_field_id"], ["tracked_fields.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_correction_records_space_id", "correction_records", ["space_id"], unique=False)
    op.create_index("ix_correction_records_status", "correction_records", ["status"], unique=False)
    op.create_index("ix_correction_records_tracked_field_id", "correction_records", ["tracked_field_id"], unique=False)
    op.create_index("ix_correction_records_document_id", "correction_records", ["document_id"], unique=False)
    op.create_index("ix_correction_records_entity_id", "correction_records", ["entity_id"], unique=False)
    op.create_index("ix_correction_records_chat_session_id", "correction_records", ["chat_session_id"], unique=False)

    op.create_table(
        "tracked_field_values",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tracked_field_id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("resolved_from_correction_id", sa.Uuid(), nullable=True),
        sa.Column("source_tier", sa.String(length=32), nullable=False),
        sa.Column("value_text", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["resolved_from_correction_id"], ["correction_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tracked_field_id"], ["tracked_fields.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tracked_field_values_tracked_field_id", "tracked_field_values", ["tracked_field_id"], unique=False)
    op.create_index("ix_tracked_field_values_space_id", "tracked_field_values", ["space_id"], unique=False)
    op.create_index("ix_tracked_field_values_created_at", "tracked_field_values", ["created_at"], unique=False)
    op.create_index(
        "ux_tracked_field_values_current_per_field",
        "tracked_field_values",
        ["tracked_field_id"],
        unique=True,
        postgresql_where=sa.text("is_current"),
        sqlite_where=sa.text("is_current = 1"),
    )

    op.create_table(
        "change_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("tracked_field_id", sa.Uuid(), nullable=True),
        sa.Column("correction_id", sa.Uuid(), nullable=True),
        sa.Column("chat_session_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["chat_session_id"], ["chat_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["correction_id"], ["correction_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tracked_field_id"], ["tracked_fields.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_change_events_space_id", "change_events", ["space_id"], unique=False)
    op.create_index("ix_change_events_event_type", "change_events", ["event_type"], unique=False)
    op.create_index("ix_change_events_created_at", "change_events", ["created_at"], unique=False)
    op.create_index("ix_change_events_document_id", "change_events", ["document_id"], unique=False)
    op.create_index("ix_change_events_tracked_field_id", "change_events", ["tracked_field_id"], unique=False)
    op.create_index("ix_change_events_correction_id", "change_events", ["correction_id"], unique=False)

    op.create_table(
        "change_event_reads",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("change_event_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["change_event_id"], ["change_events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("change_event_id", "user_id", name="ux_change_event_reads_event_user"),
    )
    op.create_index("ix_change_event_reads_user_id", "change_event_reads", ["user_id"], unique=False)
    op.create_index("ix_change_event_reads_change_event_id", "change_event_reads", ["change_event_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_change_event_reads_change_event_id", table_name="change_event_reads")
    op.drop_index("ix_change_event_reads_user_id", table_name="change_event_reads")
    op.drop_table("change_event_reads")
    op.drop_index("ix_change_events_correction_id", table_name="change_events")
    op.drop_index("ix_change_events_tracked_field_id", table_name="change_events")
    op.drop_index("ix_change_events_document_id", table_name="change_events")
    op.drop_index("ix_change_events_created_at", table_name="change_events")
    op.drop_index("ix_change_events_event_type", table_name="change_events")
    op.drop_index("ix_change_events_space_id", table_name="change_events")
    op.drop_table("change_events")
    op.drop_index("ux_tracked_field_values_current_per_field", table_name="tracked_field_values")
    op.drop_index("ix_tracked_field_values_created_at", table_name="tracked_field_values")
    op.drop_index("ix_tracked_field_values_space_id", table_name="tracked_field_values")
    op.drop_index("ix_tracked_field_values_tracked_field_id", table_name="tracked_field_values")
    op.drop_table("tracked_field_values")
    op.drop_index("ix_correction_records_chat_session_id", table_name="correction_records")
    op.drop_index("ix_correction_records_entity_id", table_name="correction_records")
    op.drop_index("ix_correction_records_document_id", table_name="correction_records")
    op.drop_index("ix_correction_records_tracked_field_id", table_name="correction_records")
    op.drop_index("ix_correction_records_status", table_name="correction_records")
    op.drop_index("ix_correction_records_space_id", table_name="correction_records")
    op.drop_table("correction_records")
    op.drop_index("ix_chat_messages_created_at", table_name="chat_messages")
    op.drop_index("ix_chat_messages_space_id", table_name="chat_messages")
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_tracked_fields_is_active", table_name="tracked_fields")
    op.drop_index("ix_tracked_fields_owner_user_id", table_name="tracked_fields")
    op.drop_index("ix_tracked_fields_space_id", table_name="tracked_fields")
    op.drop_table("tracked_fields")
    op.drop_index("ix_chat_sessions_updated_at", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_owner_user_id", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_space_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
