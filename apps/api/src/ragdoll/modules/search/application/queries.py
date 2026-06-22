from __future__ import annotations

import math
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import Citation, SourceTier, SpaceScope
from ragdoll.core.exceptions import ApplicationError
from ragdoll.core.exceptions import ConfigurationError
from ragdoll.core.pagination import PaginationParams
from ragdoll.modules.search.api.schemas import (
    SearchEntitySummary,
    SearchMode,
    SearchResponse,
    SearchResult,
    SearchResultDocument,
)
from ragdoll.modules.search.infrastructure.repository import (
    ChunkSearchRecord,
    EntitySearchRecord,
    SearchFilters,
    SearchRepository,
    VectorSearchRecord,
)
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids
from ragdoll.platform.db.models import CanonicalEntity, Document, DocumentChunk, Entity
from ragdoll.platform.llm import DeterministicEmbeddingService, get_embedding_generation_service


@dataclass
class SearchCandidate:
    dedupe_key: str
    score: float
    result: SearchResult
    matched_modes: set[SearchMode]


def _owner_user_id(subject: str) -> UUID:
    return UUID(subject)


def _query_terms(query_text: str) -> list[str]:
    return [term for term in re.findall(r"[a-z0-9]+", query_text.lower()) if term]


def _chunk_locator(chunk: DocumentChunk) -> str:
    return f"chunk:{chunk.chunk_index + 1}"


def _chunk_citation(document: Document, chunk: DocumentChunk, *, source_tier: SourceTier) -> Citation:
    return Citation(
        document_id=document.id,
        chunk_id=str(chunk.id),
        title=document.title,
        locator=_chunk_locator(chunk),
        source_tier=source_tier,
    )


def _document_summary(document: Document) -> SearchResultDocument:
    return SearchResultDocument(
        id=document.id,
        space_id=document.space_id,
        title=document.title,
        file_type=document.file_type,
        created_at=document.created_at,
    )


def _entity_summary(entity: CanonicalEntity, *, mention_count: int | None = None) -> SearchEntitySummary:
    return SearchEntitySummary(
        id=entity.id,
        entity_type=entity.entity_type,
        display_name=entity.display_name,
        normalized_name=entity.normalized_name,
        mention_count=mention_count,
    )


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(component * component for component in left))
    right_norm = math.sqrt(sum(component * component for component in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def _query_embedding(query_text: str, *, prefer_deterministic: bool = False) -> list[float] | None:
    if prefer_deterministic:
        try:
            return DeterministicEmbeddingService().generate_embeddings([query_text])[0]
        except Exception:
            return None
    try:
        return get_embedding_generation_service().generate_embeddings([query_text])[0]
    except (ConfigurationError, IndexError, ValueError):
        try:
            return DeterministicEmbeddingService().generate_embeddings([query_text])[0]
        except Exception:
            return None


def _boolean_score(record: ChunkSearchRecord, query_text: str, terms: list[str]) -> float:
    haystack = " ".join(
        [
            record.document.title,
            record.document.original_filename,
            record.chunk.text_content,
        ]
    ).lower()
    if not haystack:
        return 0.0
    exact_phrase_bonus = 3.0 if query_text.lower() in haystack else 0.0
    token_hits = sum(haystack.count(term) for term in terms)
    return exact_phrase_bonus + float(token_hits)


def _graph_score(record: EntitySearchRecord, query_text: str, terms: list[str]) -> float:
    normalized_name = record.entity.normalized_name.lower()
    display_name = record.entity.display_name.lower()
    exact_phrase_bonus = 3.0 if query_text.lower() in normalized_name or query_text.lower() in display_name else 0.0
    token_hits = sum(
        1.0
        for term in terms
        if term in normalized_name or term in display_name or term in record.entity.entity_type.lower()
    )
    return exact_phrase_bonus + token_hits + min(record.mention_count, 10) / 10.0


def _chunk_candidate(
    record: ChunkSearchRecord | VectorSearchRecord,
    *,
    mode: SearchMode,
    score: float,
    chunk_entity: CanonicalEntity | None,
) -> SearchCandidate:
    document = record.document
    chunk = record.chunk
    return SearchCandidate(
        dedupe_key=f"chunk:{chunk.id}",
        score=score,
        matched_modes={mode},
        result=SearchResult(
            result_id=str(chunk.id),
            result_kind="document_chunk",
            score=round(score, 6),
            matched_modes=[mode],
            document=_document_summary(document),
            preview_text=chunk.text_preview,
            entity=_entity_summary(chunk_entity) if chunk_entity is not None else None,
            citations=[_chunk_citation(document, chunk, source_tier=SourceTier.DOCUMENT)],
        ),
    )


def _graph_candidate(
    record: EntitySearchRecord,
    *,
    score: float,
    mention: Entity | None,
    mention_document: Document | None,
) -> SearchCandidate:
    citations: list[Citation] = []
    preview_text = record.entity.display_name
    if mention is not None and mention_document is not None:
        citations.append(
            Citation(
                document_id=mention.document_id,
                entity_id=record.entity.id,
                chunk_id=str(mention.chunk_id),
                title=mention_document.title,
                locator=f"chunk-source:{mention.chunk_id}",
                source_tier=SourceTier.DERIVED,
            )
        )
        preview_text = mention.surface_text

    return SearchCandidate(
        dedupe_key=f"entity:{record.entity.id}",
        score=score,
        matched_modes={SearchMode.GRAPH},
        result=SearchResult(
            result_id=str(record.entity.id),
            result_kind="entity",
            score=round(score, 6),
            matched_modes=[SearchMode.GRAPH],
            document=_document_summary(mention_document) if mention_document is not None else None,
            preview_text=preview_text,
            entity=_entity_summary(record.entity, mention_count=record.mention_count),
            citations=citations,
        ),
    )


def _merge_candidates(candidates: list[SearchCandidate]) -> list[SearchCandidate]:
    merged: dict[str, SearchCandidate] = {}
    for candidate in candidates:
        existing = merged.get(candidate.dedupe_key)
        if existing is None:
            merged[candidate.dedupe_key] = candidate
            continue
        existing.score = max(existing.score, candidate.score)
        existing.matched_modes.update(candidate.matched_modes)
        existing.result.score = round(existing.score, 6)
        existing.result.matched_modes = sorted(existing.matched_modes, key=lambda value: value.value)
        if existing.result.entity is None and candidate.result.entity is not None:
            existing.result.entity = candidate.result.entity
        if existing.result.document is None and candidate.result.document is not None:
            existing.result.document = candidate.result.document
        seen_citations = {
            (
                citation.document_id,
                citation.entity_id,
                citation.chunk_id,
                citation.locator,
                citation.source_tier,
            )
            for citation in existing.result.citations
        }
        for citation in candidate.result.citations:
            key = (
                citation.document_id,
                citation.entity_id,
                citation.chunk_id,
                citation.locator,
                citation.source_tier,
            )
            if key not in seen_citations:
                existing.result.citations.append(citation)
                seen_citations.add(key)
    return sorted(
        merged.values(),
        key=lambda candidate: (
            -candidate.score,
            -(candidate.result.document.created_at.timestamp() if candidate.result.document is not None else 0.0),
            candidate.result.result_kind,
            candidate.result.result_id,
        ),
    )


def search_documents(
    session: Session,
    subject: str,
    pagination: PaginationParams,
    *,
    space_scope: SpaceScope,
    query_text: str,
    mode: SearchMode,
    document_id: UUID | None,
    file_type: str | None,
    entity_type: str | None,
) -> SearchResponse:
    owner_user_id = _owner_user_id(subject)
    repo = SearchRepository(session)
    space_ids = resolve_owned_space_ids(session, owner_user_id, space_scope)
    filters = SearchFilters(document_id=document_id, file_type=file_type, entity_type=entity_type)
    query_text = query_text.strip()
    if not query_text:
        raise ApplicationError(
            "q must not be blank.",
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        )
    terms = _query_terms(query_text)

    merged_candidates: list[SearchCandidate] = []

    if mode in {SearchMode.BOOLEAN, SearchMode.COMBINED}:
        boolean_records = repo.list_boolean_records(space_ids, filters=filters)
        chunk_entities = repo.chunk_entity_map([record.chunk.id for record in boolean_records])
        boolean_candidates = [
            _chunk_candidate(
                record,
                mode=SearchMode.BOOLEAN,
                score=_boolean_score(record, query_text, terms),
                chunk_entity=chunk_entities.get(record.chunk.id),
            )
            for record in boolean_records
        ]
        merged_candidates.extend(candidate for candidate in boolean_candidates if candidate.score > 0)

    if mode in {SearchMode.VECTOR, SearchMode.COMBINED}:
        vector_records = repo.list_vector_records(space_ids, filters=filters)
        prefer_deterministic = bool(vector_records) and {
            record.vector.embedding_model for record in vector_records
        } == {"deterministic"}
        query_embedding = _query_embedding(query_text, prefer_deterministic=prefer_deterministic)
        if query_embedding is not None:
            chunk_entities = repo.chunk_entity_map([record.chunk.id for record in vector_records])
            vector_candidates = [
                _chunk_candidate(
                    record,
                    mode=SearchMode.VECTOR,
                    score=_cosine_similarity(query_embedding, record.vector.embedding),
                    chunk_entity=chunk_entities.get(record.chunk.id),
                )
                for record in vector_records
            ]
            merged_candidates.extend(candidate for candidate in vector_candidates if candidate.score > 0)

    if mode in {SearchMode.GRAPH, SearchMode.COMBINED}:
        graph_records = repo.list_graph_records(space_ids, filters=filters)
        latest_mentions = repo.latest_entity_mentions([record.entity.id for record in graph_records])
        documents = repo.entity_documents([mention.document_id for mention in latest_mentions.values()])
        graph_candidates = [
            _graph_candidate(
                record,
                score=_graph_score(record, query_text, terms),
                mention=latest_mentions.get(record.entity.id),
                mention_document=documents.get(latest_mentions[record.entity.id].document_id)
                if record.entity.id in latest_mentions
                else None,
            )
            for record in graph_records
        ]
        merged_candidates.extend(candidate for candidate in graph_candidates if candidate.score > 0)

    ranked = _merge_candidates(merged_candidates)
    total = len(ranked)
    page_items = ranked[pagination.offset : pagination.offset + pagination.page_size]
    return SearchResponse(
        items=[candidate.result for candidate in page_items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )
