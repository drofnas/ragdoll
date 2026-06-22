from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, aliased

from ragdoll.core.exceptions import ApplicationError
from ragdoll.platform.db.models import CanonicalEntity, Document, Entity, GraphEdge, GraphNode


@dataclass(frozen=True)
class GraphEdgeRecord:
    edge: GraphEdge
    source: GraphNode
    target: GraphNode
    source_entity: CanonicalEntity
    target_entity: CanonicalEntity
    document: Document


class KnowledgeGraphRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_visible_seed_or_404(self, space_ids: list[UUID], entity_id: UUID) -> CanonicalEntity:
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

    def get_visible_document_or_404(self, space_ids: list[UUID], document_id: UUID) -> Document:
        document = self.session.scalar(
            select(Document).where(
                Document.id == document_id,
                Document.space_id.in_(space_ids),
                Document.deleted_at.is_(None),
            )
        )
        if document is None:
            raise ApplicationError(
                "Requested document was not found.",
                status_code=404,
                title="Not found",
                type_uri="https://ragdoll.dev/problems/not-found",
                code="document_not_found",
            )
        return document

    def list_edges_for_document(self, document_id: UUID, *, limit: int) -> list[GraphEdgeRecord]:
        return self._load_graph_edges(
            select(GraphEdge)
            .where(GraphEdge.document_id == document_id)
            .order_by(GraphEdge.weight.desc(), GraphEdge.id.asc())
            .limit(limit)
        )

    def list_neighbor_edges(self, canonical_entity_ids: set[UUID], *, limit: int) -> list[GraphEdgeRecord]:
        if not canonical_entity_ids:
            return []
        source_node = aliased(GraphNode)
        target_node = aliased(GraphNode)
        return self._load_graph_edges(
            select(GraphEdge)
            .join(source_node, source_node.id == GraphEdge.source_node_id)
            .join(target_node, target_node.id == GraphEdge.target_node_id)
            .where(
                or_(
                    source_node.canonical_entity_id.in_(canonical_entity_ids),
                    target_node.canonical_entity_id.in_(canonical_entity_ids),
                )
            )
            .order_by(GraphEdge.weight.desc(), GraphEdge.id.asc())
            .limit(limit)
        )

    def _load_graph_edges(self, edge_stmt) -> list[GraphEdgeRecord]:
        edges = list(self.session.scalars(edge_stmt))
        if not edges:
            return []

        source_nodes = {
            node.id: node
            for node in self.session.scalars(
                select(GraphNode).where(
                    GraphNode.id.in_({edge.source_node_id for edge in edges} | {edge.target_node_id for edge in edges})
                )
            )
        }
        canonical_entities = {
            entity.id: entity
            for entity in self.session.scalars(
                select(CanonicalEntity).where(
                    CanonicalEntity.id.in_({node.canonical_entity_id for node in source_nodes.values()})
                )
            )
        }
        documents = {
            document.id: document
            for document in self.session.scalars(
                select(Document).where(Document.id.in_({edge.document_id for edge in edges}))
            )
        }
        return [
            GraphEdgeRecord(
                edge=edge,
                source=source_nodes[edge.source_node_id],
                target=source_nodes[edge.target_node_id],
                source_entity=canonical_entities[source_nodes[edge.source_node_id].canonical_entity_id],
                target_entity=canonical_entities[source_nodes[edge.target_node_id].canonical_entity_id],
                document=documents[edge.document_id],
            )
            for edge in edges
            if edge.source_node_id in source_nodes
            and edge.target_node_id in source_nodes
            and edge.document_id in documents
        ]
