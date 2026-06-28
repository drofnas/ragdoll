from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations
from typing import Callable, Protocol
from uuid import UUID

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from ragdoll.core.config import get_settings
from ragdoll.platform.db.models import CanonicalEntity, Document, Entity, GraphEdge, GraphNode
from ragdoll.platform.db.session import get_session_factory


class GraphCleanupService(Protocol):
    """Delete or rebuild graph projections for one document."""

    def cleanup_document(self, document_id: UUID) -> bool: ...

    def project_document_relationships(
        self,
        session: Session,
        *,
        document: Document,
        on_chunk_processed: Callable[[int, int], None] | None = None,
    ) -> tuple[int, int]: ...


@dataclass
class InMemoryGraphCleanupService:
    cleaned_document_ids: set[UUID] = field(default_factory=set)
    projected_node_ids: set[UUID] = field(default_factory=set)
    projected_edge_ids: set[UUID] = field(default_factory=set)

    def cleanup_document(self, document_id: UUID) -> bool:
        already_cleaned = document_id in self.cleaned_document_ids
        self.cleaned_document_ids.add(document_id)
        return not already_cleaned

    def project_document_relationships(
        self,
        session: Session,
        *,
        document: Document,
        on_chunk_processed: Callable[[int, int], None] | None = None,
    ) -> tuple[int, int]:
        del session, document, on_chunk_processed
        return 0, 0


class SqlGraphCleanupService:
    def cleanup_document(self, document_id: UUID) -> bool:
        session = get_session_factory()()
        try:
            result = session.execute(delete(GraphEdge).where(GraphEdge.document_id == document_id))
            session.commit()
            self._prune_orphan_canonical_entities(session)
            session.commit()
            return bool(result.rowcount)
        finally:
            session.close()

    def project_document_relationships(
        self,
        session: Session,
        *,
        document: Document,
        on_chunk_processed: Callable[[int, int], None] | None = None,
    ) -> tuple[int, int]:
        session.execute(delete(GraphEdge).where(GraphEdge.document_id == document.id))

        chunks = sorted(list(document.chunks), key=lambda chunk: chunk.chunk_index)
        total_chunks = len(chunks)
        mentions = list(
            session.scalars(
                select(Entity)
                .where(Entity.document_id == document.id)
                .order_by(Entity.chunk_id.asc(), Entity.normalized_name.asc())
            )
        )
        nodes_by_canonical: dict[UUID, GraphNode] = {}
        if mentions:
            canonical_ids = {mention.canonical_entity_id for mention in mentions}
            nodes_by_canonical = self._ensure_nodes(session, canonical_ids)

        mentions_by_chunk: dict[UUID, list[Entity]] = {}
        for mention in mentions:
            mentions_by_chunk.setdefault(mention.chunk_id, []).append(mention)

        edge_count = 0
        processed_chunk_count = 0
        for chunk in chunks:
            chunk_mentions = mentions_by_chunk.get(chunk.id, [])
            unique_nodes = sorted(
                {
                    nodes_by_canonical[mention.canonical_entity_id].id
                    for mention in chunk_mentions
                    if mention.canonical_entity_id in nodes_by_canonical
                },
                key=str,
            )
            for source_node_id, target_node_id in combinations(unique_nodes, 2):
                session.add(
                    GraphEdge(
                        space_id=document.space_id,
                        document_id=document.id,
                        chunk_id=chunk.id,
                        source_node_id=source_node_id,
                        target_node_id=target_node_id,
                        relation_type="co_occurs",
                        provenance_locator=f"chunk:{chunk.id}",
                        weight=1.0,
                    )
                )
                edge_count += 1
            processed_chunk_count += 1
            if on_chunk_processed is not None:
                on_chunk_processed(processed_chunk_count, total_chunks)

        return len(nodes_by_canonical), edge_count

    def _ensure_nodes(self, session: Session, canonical_ids: set[UUID]) -> dict[UUID, GraphNode]:
        if not canonical_ids:
            return {}
        canonical_entities = list(
            session.scalars(select(CanonicalEntity).where(CanonicalEntity.id.in_(canonical_ids)))
        )
        existing = {
            node.canonical_entity_id: node
            for node in session.scalars(select(GraphNode).where(GraphNode.canonical_entity_id.in_(canonical_ids)))
        }
        for canonical in canonical_entities:
            if canonical.id in existing:
                node = existing[canonical.id]
                node.label = canonical.display_name
                node.node_type = canonical.entity_type
                continue
            node = GraphNode(
                space_id=canonical.space_id,
                canonical_entity_id=canonical.id,
                node_type=canonical.entity_type,
                label=canonical.display_name,
            )
            session.add(node)
            session.flush()
            existing[canonical.id] = node
        return existing

    def _prune_orphan_canonical_entities(self, session: Session) -> None:
        session.execute(
            delete(CanonicalEntity).where(
                ~exists(select(Entity.id).where(Entity.canonical_entity_id == CanonicalEntity.id))
            )
        )


@lru_cache(maxsize=1)
def get_graph_cleanup_service() -> GraphCleanupService:
    settings = get_settings()
    if settings.e2e_shared_backends:
        return SqlGraphCleanupService()
    if settings.e2e_memory_backends:
        return InMemoryGraphCleanupService()
    return SqlGraphCleanupService()
