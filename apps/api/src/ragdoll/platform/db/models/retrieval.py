from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy import Uuid as SqlUuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON as JsonType
from sqlalchemy.types import Text as TextType
from sqlalchemy.types import TypeDecorator

from ragdoll.platform.db.models_base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class EmbeddingVectorType(TypeDecorator):
    """Store vectors in SQLite JSON and as pgvector-compatible text elsewhere."""

    impl = JsonType
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(JsonType())
        return dialect.type_descriptor(TextType())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        normalized = [float(component) for component in value]
        if dialect.name == "sqlite":
            return normalized
        return "[" + ",".join(f"{component:.12g}" for component in normalized) + "]"

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, list):
            return [float(component) for component in value]
        if isinstance(value, str):
            decoded = json.loads(value)
            return [float(component) for component in decoded]
        return [float(component) for component in value]


class DocumentChunkVector(Base):
    """Durable vector projection for one document chunk."""

    __tablename__ = "document_chunk_vectors"
    __table_args__ = (
        Index("ix_document_chunk_vectors_document_id", "document_id"),
        Index("ix_document_chunk_vectors_space_id", "space_id"),
        Index("ix_document_chunk_vectors_chunk_index", "chunk_index"),
    )

    chunk_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        primary_key=True,
    )
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
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(120), nullable=False)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(EmbeddingVectorType(), nullable=False)
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


class CanonicalEntity(Base):
    """Space-scoped canonical entity record derived from extracted mentions."""

    __tablename__ = "canonical_entities"
    __table_args__ = (
        UniqueConstraint("space_id", "entity_type", "normalized_name", name="ux_canonical_entities_space_type_name"),
        Index("ix_canonical_entities_space_id", "space_id"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
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

    mentions: Mapped[list["Entity"]] = relationship(back_populates="canonical_entity")
    graph_node: Mapped["GraphNode | None"] = relationship(back_populates="canonical_entity", uselist=False)


class Entity(Base):
    """Extracted entity mention tied to a document chunk."""

    __tablename__ = "entities"
    __table_args__ = (
        Index("ix_entities_document_id", "document_id"),
        Index("ix_entities_space_id", "space_id"),
        Index("ix_entities_chunk_id", "chunk_id"),
        Index("ix_entities_canonical_entity_id", "canonical_entity_id"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    canonical_entity_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("canonical_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    surface_text: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    extraction_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
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

    canonical_entity: Mapped[CanonicalEntity] = relationship(back_populates="mentions")


class GraphNode(Base):
    """Derived graph node for one canonical entity."""

    __tablename__ = "graph_nodes"
    __table_args__ = (
        UniqueConstraint("canonical_entity_id", name="ux_graph_nodes_canonical_entity_id"),
        Index("ix_graph_nodes_space_id", "space_id"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    canonical_entity_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("canonical_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    node_type: Mapped[str] = mapped_column(String(80), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
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

    canonical_entity: Mapped[CanonicalEntity] = relationship(back_populates="graph_node")


class GraphEdge(Base):
    """Derived graph edge for chunk-level entity co-occurrence."""

    __tablename__ = "graph_edges"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_id",
            "source_node_id",
            "target_node_id",
            "relation_type",
            name="ux_graph_edges_document_chunk_relation",
        ),
        Index("ix_graph_edges_document_id", "document_id"),
        Index("ix_graph_edges_space_id", "space_id"),
        Index("ix_graph_edges_source_node_id", "source_node_id"),
        Index("ix_graph_edges_target_node_id", "target_node_id"),
    )

    id: Mapped[UUID] = mapped_column(SqlUuid, primary_key=True, default=uuid4)
    space_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("spaces.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("document_chunks.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_node_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_node_id: Mapped[UUID] = mapped_column(
        SqlUuid,
        ForeignKey("graph_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String(80), nullable=False, default="co_occurs")
    provenance_locator: Mapped[str] = mapped_column(Text, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
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
