from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import Citation, SourceTier, SpaceScope
from ragdoll.core.pagination import PaginationParams
from ragdoll.modules.entities.api.schemas import (
    EntityDetailResponse,
    EntityHistoryEntry,
    EntityListItem,
    EntityListResponse,
    EntityMentionRecord,
    EntityRelatedDocument,
)
from ragdoll.modules.entities.infrastructure.repository import EntitiesRepository, EntityListFilters
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids
from ragdoll.platform.db.models import CanonicalEntity, Document, Entity


def _owner_user_id(subject: str) -> UUID:
    return UUID(subject)


def _mention_citation(document: Document, mention: Entity, *, source_tier: SourceTier) -> Citation:
    return Citation(
        document_id=document.id,
        entity_id=mention.canonical_entity_id,
        chunk_id=str(mention.chunk_id),
        title=document.title,
        locator=f"chunk:{mention.chunk_id}",
        source_tier=source_tier,
    )


def _build_list_item(
    entity: CanonicalEntity,
    *,
    graph_node_id: UUID | None,
    mention_count: int,
    document_count: int,
    latest_mentioned_at,
) -> EntityListItem:
    return EntityListItem(
        id=entity.id,
        space_id=entity.space_id,
        entity_type=entity.entity_type,
        display_name=entity.display_name,
        normalized_name=entity.normalized_name,
        graph_node_id=graph_node_id,
        mention_count=mention_count,
        document_count=document_count,
        latest_mentioned_at=latest_mentioned_at,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def list_entities(
    session: Session,
    subject: str,
    pagination: PaginationParams,
    *,
    space_scope: SpaceScope,
    query_text: str | None,
    entity_type: str | None,
) -> EntityListResponse:
    owner_user_id = _owner_user_id(subject)
    space_ids = resolve_owned_space_ids(session, owner_user_id, space_scope)
    repo = EntitiesRepository(session)
    items, total = repo.list_visible(
        space_ids,
        pagination,
        filters=EntityListFilters(
            query=query_text.strip().lower() if query_text and query_text.strip() else None,
            entity_type=entity_type,
        ),
    )
    return EntityListResponse(
        items=[
            _build_list_item(
                item.entity,
                graph_node_id=item.graph_node_id,
                mention_count=item.mention_count,
                document_count=item.document_count,
                latest_mentioned_at=item.latest_mentioned_at,
            )
            for item in items
        ],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_entity_detail(
    session: Session,
    subject: str,
    entity_id: UUID,
    *,
    space_scope: SpaceScope,
) -> EntityDetailResponse:
    owner_user_id = _owner_user_id(subject)
    space_ids = resolve_owned_space_ids(session, owner_user_id, space_scope)
    repo = EntitiesRepository(session)
    repo.get_visible_or_404(space_ids, entity_id)
    aggregate = repo.aggregate_for_entity(entity_id)
    mentions = repo.list_mentions(entity_id)
    related_documents = repo.list_related_documents(entity_id)

    provenance = [
        EntityMentionRecord(
            mention_id=mention.id,
            document_id=document.id,
            chunk_id=mention.chunk_id,
            surface_text=mention.surface_text,
            normalized_name=mention.normalized_name,
            confidence_score=mention.confidence_score,
            extraction_metadata=mention.extraction_metadata,
            created_at=mention.created_at,
            citation=_mention_citation(document, mention, source_tier=SourceTier.DOCUMENT),
        )
        for mention, document in mentions
    ]
    history = [
        EntityHistoryEntry(
            mention_id=mention.id,
            document_id=document.id,
            surface_text=mention.surface_text,
            observed_at=mention.created_at,
            citation=_mention_citation(document, mention, source_tier=SourceTier.DOCUMENT),
        )
        for mention, document in mentions
    ]
    documents = [
        EntityRelatedDocument(
            document_id=document.id,
            title=document.title,
            file_type=document.file_type,
            mention_count=mention_count,
            latest_mentioned_at=latest_mentioned_at,
            citation=_mention_citation(document, latest_mention, source_tier=SourceTier.DERIVED)
            if latest_mention is not None
            else None,
        )
        for document, mention_count, latest_mentioned_at, latest_mention in related_documents
    ]

    base = _build_list_item(
        aggregate.entity,
        graph_node_id=aggregate.graph_node_id,
        mention_count=aggregate.mention_count,
        document_count=aggregate.document_count,
        latest_mentioned_at=aggregate.latest_mentioned_at,
    )
    return EntityDetailResponse(
        **base.model_dump(),
        provenance=provenance,
        history=history,
        related_documents=documents,
    )
