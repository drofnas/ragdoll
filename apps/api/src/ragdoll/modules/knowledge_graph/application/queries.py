from __future__ import annotations

from collections import deque
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import Citation, SourceTier, SpaceScope
from ragdoll.core.exceptions import ApplicationError
from ragdoll.modules.knowledge_graph.api.schemas import GraphLinkResponse, GraphNodeResponse, GraphResponse
from ragdoll.modules.knowledge_graph.infrastructure.repository import GraphEdgeRecord, KnowledgeGraphRepository
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids


def _owner_user_id(subject: str) -> UUID:
    return UUID(subject)


def _edge_citation(record: GraphEdgeRecord) -> Citation:
    return Citation(
        document_id=record.document.id,
        entity_id=record.source_entity.id,
        chunk_id=str(record.edge.chunk_id),
        title=record.document.title,
        locator=record.edge.provenance_locator,
        source_tier=SourceTier.DERIVED,
    )


def _node_response(record_entity) -> GraphNodeResponse:
    return GraphNodeResponse(
        id=record_entity.id,
        space_id=record_entity.space_id,
        label=record_entity.display_name,
        node_type=record_entity.entity_type,
    )


def _graph_response(
    *,
    nodes_by_id: dict[UUID, GraphNodeResponse],
    links: list[GraphLinkResponse],
    seed_entity_id: UUID | None,
    document_id: UUID | None,
    depth: int,
) -> GraphResponse:
    return GraphResponse(
        seed_entity_id=seed_entity_id,
        document_id=document_id,
        depth=depth,
        nodes=list(nodes_by_id.values()),
        links=links,
    )


def get_entity_subgraph(
    session: Session,
    subject: str,
    entity_id: UUID,
    *,
    space_scope: SpaceScope,
    depth: int,
    limit: int,
) -> GraphResponse:
    if depth < 1 or depth > 3:
        raise ApplicationError(
            "depth must be between 1 and 3.",
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        )
    owner_user_id = _owner_user_id(subject)
    space_ids = resolve_owned_space_ids(session, owner_user_id, space_scope)
    repo = KnowledgeGraphRepository(session)
    repo.get_visible_seed_or_404(space_ids, entity_id)

    frontier = deque([(entity_id, 0)])
    seen_entities = {entity_id}
    nodes_by_id: dict[UUID, GraphNodeResponse] = {}
    links: list[GraphLinkResponse] = []
    seen_edge_keys: set[tuple[UUID, UUID, UUID]] = set()

    while frontier and len(links) < limit:
        current_entity_id, current_depth = frontier.popleft()
        if current_depth >= depth:
            continue
        edge_records = repo.list_neighbor_edges({current_entity_id}, limit=limit * 4)
        for record in edge_records:
            if (
                record.source_entity.space_id not in space_ids
                or record.target_entity.space_id not in space_ids
                or record.document.deleted_at is not None
            ):
                continue
            edge_key = (record.document.id, record.source_entity.id, record.target_entity.id)
            if edge_key in seen_edge_keys:
                continue
            seen_edge_keys.add(edge_key)
            nodes_by_id.setdefault(record.source_entity.id, _node_response(record.source_entity))
            nodes_by_id.setdefault(record.target_entity.id, _node_response(record.target_entity))
            links.append(
                GraphLinkResponse(
                    source_id=record.source_entity.id,
                    target_id=record.target_entity.id,
                    relation_type=record.edge.relation_type,
                    weight=record.edge.weight,
                    citations=[_edge_citation(record)],
                )
            )
            for next_entity_id in (record.source_entity.id, record.target_entity.id):
                if next_entity_id not in seen_entities:
                    seen_entities.add(next_entity_id)
                    frontier.append((next_entity_id, current_depth + 1))
            if len(links) >= limit:
                break

    if entity_id not in nodes_by_id:
        seed = repo.get_visible_seed_or_404(space_ids, entity_id)
        nodes_by_id[entity_id] = _node_response(seed)
    return _graph_response(
        nodes_by_id=nodes_by_id,
        links=links,
        seed_entity_id=entity_id,
        document_id=None,
        depth=depth,
    )


def get_document_graph(
    session: Session,
    subject: str,
    document_id: UUID,
    *,
    space_scope: SpaceScope,
    limit: int,
) -> GraphResponse:
    owner_user_id = _owner_user_id(subject)
    space_ids = resolve_owned_space_ids(session, owner_user_id, space_scope)
    repo = KnowledgeGraphRepository(session)
    repo.get_visible_document_or_404(space_ids, document_id)

    nodes_by_id: dict[UUID, GraphNodeResponse] = {}
    links: list[GraphLinkResponse] = []
    for record in repo.list_edges_for_document(document_id, limit=limit):
        nodes_by_id.setdefault(record.source_entity.id, _node_response(record.source_entity))
        nodes_by_id.setdefault(record.target_entity.id, _node_response(record.target_entity))
        links.append(
            GraphLinkResponse(
                source_id=record.source_entity.id,
                target_id=record.target_entity.id,
                relation_type=record.edge.relation_type,
                weight=record.edge.weight,
                citations=[_edge_citation(record)],
            )
        )
    return _graph_response(
        nodes_by_id=nodes_by_id,
        links=links,
        seed_entity_id=None,
        document_id=document_id,
        depth=1,
    )
