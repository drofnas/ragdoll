from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from ragdoll.platform.db.models import CanonicalEntity, Document, DocumentChunk, DocumentChunkVector, Entity, GraphNode


@dataclass(frozen=True)
class SearchFilters:
    document_id: UUID | None = None
    file_type: str | None = None
    entity_type: str | None = None


@dataclass(frozen=True)
class ChunkSearchRecord:
    document: Document
    chunk: DocumentChunk


@dataclass(frozen=True)
class VectorSearchRecord:
    document: Document
    chunk: DocumentChunk
    vector: DocumentChunkVector


@dataclass(frozen=True)
class EntitySearchRecord:
    entity: CanonicalEntity
    graph_node_id: UUID | None
    mention_count: int
    document_count: int


class SearchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _document_scope_stmt(self, space_ids: list[UUID], *, filters: SearchFilters):
        stmt = (
            select(Document)
            .where(
                Document.space_id.in_(space_ids),
                Document.deleted_at.is_(None),
            )
        )
        if filters.document_id is not None:
            stmt = stmt.where(Document.id == filters.document_id)
        if filters.file_type is not None:
            stmt = stmt.where(Document.file_type == filters.file_type)
        return stmt

    def _chunk_stmt(self, space_ids: list[UUID], *, filters: SearchFilters):
        document_subquery = self._document_scope_stmt(space_ids, filters=filters).subquery()
        stmt = (
            select(DocumentChunk, Document)
            .join(document_subquery, DocumentChunk.document_id == document_subquery.c.id)
            .join(Document, Document.id == DocumentChunk.document_id)
        )
        if filters.entity_type is not None:
            stmt = stmt.join(Entity, Entity.chunk_id == DocumentChunk.id).where(Entity.entity_type == filters.entity_type)
        return stmt.order_by(Document.created_at.desc(), DocumentChunk.chunk_index.asc())

    def list_boolean_records(self, space_ids: list[UUID], *, filters: SearchFilters) -> list[ChunkSearchRecord]:
        rows = self.session.execute(self._chunk_stmt(space_ids, filters=filters)).all()
        unique: dict[UUID, ChunkSearchRecord] = {}
        for chunk, document in rows:
            unique.setdefault(chunk.id, ChunkSearchRecord(document=document, chunk=chunk))
        return list(unique.values())

    def list_vector_records(self, space_ids: list[UUID], *, filters: SearchFilters) -> list[VectorSearchRecord]:
        document_subquery = self._document_scope_stmt(space_ids, filters=filters).subquery()
        stmt = (
            select(DocumentChunkVector, DocumentChunk, Document)
            .join(DocumentChunk, DocumentChunk.id == DocumentChunkVector.chunk_id)
            .join(document_subquery, DocumentChunkVector.document_id == document_subquery.c.id)
            .join(Document, Document.id == DocumentChunkVector.document_id)
        )
        if filters.entity_type is not None:
            stmt = stmt.join(Entity, Entity.chunk_id == DocumentChunk.id).where(Entity.entity_type == filters.entity_type)
        rows = self.session.execute(
            stmt.order_by(Document.created_at.desc(), DocumentChunkVector.chunk_index.asc())
        ).all()
        unique: dict[UUID, VectorSearchRecord] = {}
        for vector, chunk, document in rows:
            unique.setdefault(chunk.id, VectorSearchRecord(document=document, chunk=chunk, vector=vector))
        return list(unique.values())

    def chunk_entity_map(self, chunk_ids: list[UUID]) -> dict[UUID, CanonicalEntity]:
        if not chunk_ids:
            return {}
        rows = self.session.execute(
            select(Entity.chunk_id, CanonicalEntity)
            .join(CanonicalEntity, CanonicalEntity.id == Entity.canonical_entity_id)
            .where(Entity.chunk_id.in_(chunk_ids))
            .order_by(Entity.chunk_id.asc(), CanonicalEntity.display_name.asc())
        ).all()
        result: dict[UUID, CanonicalEntity] = {}
        for chunk_id, canonical in rows:
            result.setdefault(chunk_id, canonical)
        return result

    def list_graph_records(
        self,
        space_ids: list[UUID],
        *,
        filters: SearchFilters,
    ) -> list[EntitySearchRecord]:
        stmt = (
            select(
                CanonicalEntity,
                GraphNode.id,
                func.count(Entity.id),
                func.count(func.distinct(Entity.document_id)),
            )
            .join(Entity, Entity.canonical_entity_id == CanonicalEntity.id)
            .join(Document, Document.id == Entity.document_id)
            .outerjoin(GraphNode, GraphNode.canonical_entity_id == CanonicalEntity.id)
            .where(
                CanonicalEntity.space_id.in_(space_ids),
                Document.deleted_at.is_(None),
            )
            .group_by(CanonicalEntity.id, GraphNode.id)
            .order_by(func.count(Entity.id).desc(), CanonicalEntity.display_name.asc())
        )
        if filters.document_id is not None:
            stmt = stmt.where(Document.id == filters.document_id)
        if filters.file_type is not None:
            stmt = stmt.where(Document.file_type == filters.file_type)
        if filters.entity_type is not None:
            stmt = stmt.where(CanonicalEntity.entity_type == filters.entity_type)
        rows = self.session.execute(stmt).all()
        return [
            EntitySearchRecord(
                entity=entity,
                graph_node_id=graph_node_id,
                mention_count=int(mention_count or 0),
                document_count=int(document_count or 0),
            )
            for entity, graph_node_id, mention_count, document_count in rows
        ]

    def latest_entity_mentions(self, canonical_entity_ids: list[UUID]) -> dict[UUID, Entity]:
        if not canonical_entity_ids:
            return {}
        rows = self.session.execute(
            select(Entity)
            .join(Document, Document.id == Entity.document_id)
            .where(Entity.canonical_entity_id.in_(canonical_entity_ids))
            .where(Document.deleted_at.is_(None))
            .order_by(Entity.canonical_entity_id.asc(), Entity.created_at.desc(), Entity.id.desc())
        ).scalars()
        result: dict[UUID, Entity] = {}
        for mention in rows:
            result.setdefault(mention.canonical_entity_id, mention)
        return result

    def entity_documents(self, document_ids: list[UUID]) -> dict[UUID, Document]:
        if not document_ids:
            return {}
        documents = self.session.scalars(select(Document).where(Document.id.in_(document_ids))).all()
        return {document.id: document for document in documents}
