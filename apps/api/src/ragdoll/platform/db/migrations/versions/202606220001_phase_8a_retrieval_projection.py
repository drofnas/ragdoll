"""phase_8a_retrieval_projection

Revision ID: 202606220001
Revises: 202606200002
Create Date: 2026-06-22 00:01:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "202606220001"
down_revision = "202606200002"
branch_labels = None
depends_on = None


class VectorType(sa.types.UserDefinedType):
    def get_col_spec(self, **kw):
        del kw
        return "vector(768)"


def _embedding_column() -> sa.Column:
    dialect_name = op.get_bind().dialect.name
    if dialect_name == "sqlite":
        return sa.Column("embedding", sa.JSON(), nullable=False)
    return sa.Column("embedding", VectorType(), nullable=False)


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "document_chunk_vectors",
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("checksum", sa.String(length=64), nullable=False),
        sa.Column("embedding_model", sa.String(length=120), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        _embedding_column(),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("chunk_id"),
    )
    op.create_index("ix_document_chunk_vectors_document_id", "document_chunk_vectors", ["document_id"], unique=False)
    op.create_index("ix_document_chunk_vectors_space_id", "document_chunk_vectors", ["space_id"], unique=False)
    op.create_index("ix_document_chunk_vectors_chunk_index", "document_chunk_vectors", ["chunk_index"], unique=False)

    op.create_table(
        "canonical_entities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("space_id", "entity_type", "normalized_name", name="ux_canonical_entities_space_type_name"),
    )
    op.create_index("ix_canonical_entities_space_id", "canonical_entities", ["space_id"], unique=False)

    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_entity_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("surface_text", sa.String(length=255), nullable=False),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("extraction_model", sa.String(length=120), nullable=True),
        sa.Column("extraction_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["canonical_entity_id"], ["canonical_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_entities_document_id", "entities", ["document_id"], unique=False)
    op.create_index("ix_entities_space_id", "entities", ["space_id"], unique=False)
    op.create_index("ix_entities_chunk_id", "entities", ["chunk_id"], unique=False)
    op.create_index("ix_entities_canonical_entity_id", "entities", ["canonical_entity_id"], unique=False)

    op.create_table(
        "graph_nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_entity_id", sa.Uuid(), nullable=False),
        sa.Column("node_type", sa.String(length=80), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["canonical_entity_id"], ["canonical_entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("canonical_entity_id", name="ux_graph_nodes_canonical_entity_id"),
    )
    op.create_index("ix_graph_nodes_space_id", "graph_nodes", ["space_id"], unique=False)

    op.create_table(
        "graph_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("space_id", sa.Uuid(), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("chunk_id", sa.Uuid(), nullable=False),
        sa.Column("source_node_id", sa.Uuid(), nullable=False),
        sa.Column("target_node_id", sa.Uuid(), nullable=False),
        sa.Column("relation_type", sa.String(length=80), nullable=False, server_default="co_occurs"),
        sa.Column("provenance_locator", sa.Text(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["chunk_id"], ["document_chunks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_node_id"], ["graph_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["space_id"], ["spaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_node_id"], ["graph_nodes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "chunk_id",
            "source_node_id",
            "target_node_id",
            "relation_type",
            name="ux_graph_edges_document_chunk_relation",
        ),
    )
    op.create_index("ix_graph_edges_document_id", "graph_edges", ["document_id"], unique=False)
    op.create_index("ix_graph_edges_space_id", "graph_edges", ["space_id"], unique=False)
    op.create_index("ix_graph_edges_source_node_id", "graph_edges", ["source_node_id"], unique=False)
    op.create_index("ix_graph_edges_target_node_id", "graph_edges", ["target_node_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_graph_edges_target_node_id", table_name="graph_edges")
    op.drop_index("ix_graph_edges_source_node_id", table_name="graph_edges")
    op.drop_index("ix_graph_edges_space_id", table_name="graph_edges")
    op.drop_index("ix_graph_edges_document_id", table_name="graph_edges")
    op.drop_table("graph_edges")
    op.drop_index("ix_graph_nodes_space_id", table_name="graph_nodes")
    op.drop_table("graph_nodes")
    op.drop_index("ix_entities_canonical_entity_id", table_name="entities")
    op.drop_index("ix_entities_chunk_id", table_name="entities")
    op.drop_index("ix_entities_space_id", table_name="entities")
    op.drop_index("ix_entities_document_id", table_name="entities")
    op.drop_table("entities")
    op.drop_index("ix_canonical_entities_space_id", table_name="canonical_entities")
    op.drop_table("canonical_entities")
    op.drop_index("ix_document_chunk_vectors_chunk_index", table_name="document_chunk_vectors")
    op.drop_index("ix_document_chunk_vectors_space_id", table_name="document_chunk_vectors")
    op.drop_index("ix_document_chunk_vectors_document_id", table_name="document_chunk_vectors")
    op.drop_table("document_chunk_vectors")
