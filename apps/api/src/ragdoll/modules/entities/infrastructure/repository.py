from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError
from ragdoll.core.pagination import PaginationParams
from ragdoll.platform.db.models import CanonicalEntity, Document, Entity, GraphNode


@dataclass(frozen=True)
class EntityListFilters:
    query: str | None = None
    entity_type: str | None = None


@dataclass(frozen=True)
class EntityAggregateRecord:
    entity: CanonicalEntity
    graph_node_id: UUID | None
    mention_count: int
    document_count: int
    latest_mentioned_at: datetime | None


class EntitiesRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _aggregate_stmt(self, space_ids: list[UUID], *, filters: EntityListFilters):
        stmt = (
            select(
                CanonicalEntity,
                GraphNode.id,
                func.count(Entity.id),
                func.count(func.distinct(Entity.document_id)),
                func.max(Entity.created_at),
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
        if filters.entity_type is not None:
            stmt = stmt.where(CanonicalEntity.entity_type == filters.entity_type)
        if filters.query is not None:
            token = f"%{filters.query.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(CanonicalEntity.display_name).like(token),
                    func.lower(CanonicalEntity.normalized_name).like(token),
                )
            )
        return stmt

    def list_visible(
        self,
        space_ids: list[UUID],
        pagination: PaginationParams,
        *,
        filters: EntityListFilters,
    ) -> tuple[list[EntityAggregateRecord], int]:
        stmt = self._aggregate_stmt(space_ids, filters=filters)
        total = self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = self.session.execute(
            stmt.offset(pagination.offset).limit(pagination.page_size)
        ).all()
        return [
            EntityAggregateRecord(
                entity=entity,
                graph_node_id=graph_node_id,
                mention_count=int(mention_count or 0),
                document_count=int(document_count or 0),
                latest_mentioned_at=latest_mentioned_at,
            )
            for entity, graph_node_id, mention_count, document_count, latest_mentioned_at in rows
        ], int(total)

    def get_visible_or_404(self, space_ids: list[UUID], entity_id: UUID) -> CanonicalEntity:
        entity = self.session.scalar(
            select(CanonicalEntity)
            .join(Entity, Entity.canonical_entity_id == CanonicalEntity.id)
            .join(Document, Document.id == Entity.document_id)
            .where(
                CanonicalEntity.id == entity_id,
                CanonicalEntity.space_id.in_(space_ids),
                Document.deleted_at.is_(None),
            )
        )
        if entity is None:
            raise ApplicationError(
                "Requested entity was not found.",
                status_code=404,
                title="Not found",
                type_uri="https://ragdoll.dev/problems/not-found",
                code="entity_not_found",
            )
        return entity

    def aggregate_for_entity(self, entity_id: UUID) -> EntityAggregateRecord:
        row = self.session.execute(
            select(
                CanonicalEntity,
                GraphNode.id,
                func.count(Entity.id),
                func.count(func.distinct(Entity.document_id)),
                func.max(Entity.created_at),
            )
            .join(Entity, Entity.canonical_entity_id == CanonicalEntity.id)
            .join(Document, Document.id == Entity.document_id)
            .outerjoin(GraphNode, GraphNode.canonical_entity_id == CanonicalEntity.id)
            .where(
                CanonicalEntity.id == entity_id,
                Document.deleted_at.is_(None),
            )
            .group_by(CanonicalEntity.id, GraphNode.id)
        ).one()
        entity, graph_node_id, mention_count, document_count, latest_mentioned_at = row
        return EntityAggregateRecord(
            entity=entity,
            graph_node_id=graph_node_id,
            mention_count=int(mention_count or 0),
            document_count=int(document_count or 0),
            latest_mentioned_at=latest_mentioned_at,
        )

    def list_mentions(self, entity_id: UUID) -> list[tuple[Entity, Document]]:
        rows = self.session.execute(
            select(Entity, Document)
            .join(Document, Document.id == Entity.document_id)
            .where(
                Entity.canonical_entity_id == entity_id,
                Document.deleted_at.is_(None),
            )
            .order_by(Entity.created_at.asc(), Document.created_at.asc(), Entity.id.asc())
        ).all()
        return [(mention, document) for mention, document in rows]

    def list_related_documents(self, entity_id: UUID) -> list[tuple[Document, int, datetime | None, Entity | None]]:
        aggregates = self.session.execute(
            select(
                Document,
                func.count(Entity.id),
                func.max(Entity.created_at),
            )
            .join(Entity, Entity.document_id == Document.id)
            .where(
                Entity.canonical_entity_id == entity_id,
                Document.deleted_at.is_(None),
            )
            .group_by(Document.id)
            .order_by(func.max(Entity.created_at).desc(), Document.created_at.desc())
        ).all()

        latest_mentions = {
            document.id: self.session.scalar(
                select(Entity)
                .where(
                    Entity.canonical_entity_id == entity_id,
                    Entity.document_id == document.id,
                )
                .order_by(Entity.created_at.desc(), Entity.id.desc())
                .limit(1)
            )
            for document, _, _ in aggregates
        }
        return [
            (document, int(mention_count or 0), latest_mentioned_at, latest_mentions.get(document.id))
            for document, mention_count, latest_mentioned_at in aggregates
        ]
