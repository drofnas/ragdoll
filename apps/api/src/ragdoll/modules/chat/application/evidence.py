from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import Citation, SourceTier, SpaceScope
from ragdoll.modules.corrections.application.service import correction_citation, correction_matches_query
from ragdoll.modules.corrections.infrastructure.repository import CorrectionsRepository
from ragdoll.modules.knowledge_graph.infrastructure.repository import KnowledgeGraphRepository
from ragdoll.modules.search.api.schemas import SearchMode, SearchResult
from ragdoll.modules.search.application.evidence import retrieve_search_results
from ragdoll.modules.tracked_state.infrastructure.repository import TrackedStateRepository
from ragdoll.platform.db.models import ChatMessage, ChatSession


SOURCE_QUOTAS = {
    "correction": 3,
    "tracked_state": 5,
    "document_chunk": 8,
    "graph_entity": 4,
    "graph_relationship": 6,
}
TOTAL_EVIDENCE_LIMIT = 16
HISTORY_MESSAGE_LIMIT = 8


@dataclass(frozen=True)
class ChatEvidenceItem:
    id: str
    source_type: str
    source_tier: SourceTier
    text: str
    citations: list[Citation]
    score: float
    title: str | None = None
    created_at: datetime | None = None


@dataclass(frozen=True)
class ChatHistoryItem:
    role: str
    content: str
    created_at: datetime


@dataclass(frozen=True)
class ChatEvidenceBundle:
    evidence_items: list[ChatEvidenceItem]
    history_items: list[ChatHistoryItem]
    retrieval_results: list[SearchResult]


def _normalized_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _query_terms(query_text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", query_text.lower()))


def _overlap_score(query_terms: set[str], text: str) -> float:
    if not query_terms:
        return 0.0
    haystack = set(re.findall(r"[a-z0-9]+", text.lower()))
    if not haystack:
        return 0.0
    return float(len(query_terms.intersection(haystack)))


def _citation_key(citation: Citation) -> tuple[object, ...]:
    return (
        citation.document_id,
        citation.entity_id,
        citation.chunk_id,
        citation.locator,
        citation.line_number,
        citation.source_tier,
    )


def _citation_from_raw(value: object) -> Citation | None:
    if not isinstance(value, dict):
        return None
    try:
        return Citation.model_validate(value)
    except ValueError:
        return None


def _dedupe_and_rank(items: list[ChatEvidenceItem]) -> list[ChatEvidenceItem]:
    unique: dict[tuple[str, tuple[tuple[object, ...], ...]], ChatEvidenceItem] = {}
    for item in items:
        key = (_normalized_text(item.text), tuple(_citation_key(citation) for citation in item.citations))
        existing = unique.get(key)
        if existing is None or item.score > existing.score:
            unique[key] = item

    by_source: dict[str, list[ChatEvidenceItem]] = {}
    for item in sorted(unique.values(), key=lambda value: value.score, reverse=True):
        by_source.setdefault(item.source_type, []).append(item)

    quota_limited: list[ChatEvidenceItem] = []
    for source_type, source_items in by_source.items():
        quota = SOURCE_QUOTAS.get(source_type, 3)
        quota_limited.extend(source_items[:quota])

    def created_sort_value(item: ChatEvidenceItem) -> float:
        if item.created_at is None:
            return 0.0
        return item.created_at.timestamp()

    ranked = sorted(
        quota_limited,
        key=lambda item: (
            item.source_tier == SourceTier.VERIFIED,
            item.source_type == "tracked_state",
            item.source_tier == SourceTier.DOCUMENT,
            item.score,
            created_sort_value(item),
        ),
        reverse=True,
    )[:TOTAL_EVIDENCE_LIMIT]
    return [replace(item, id=f"E{index}") for index, item in enumerate(ranked, start=1)]


def _correction_evidence(session: Session, *, space_id: UUID, query_text: str) -> list[ChatEvidenceItem]:
    items: list[ChatEvidenceItem] = []
    for index, correction in enumerate(CorrectionsRepository(session).list_verified_for_space(space_id), start=1):
        if not correction_matches_query(correction, query_text):
            continue
        items.append(
            ChatEvidenceItem(
                id=f"correction-{index}",
                source_type="correction",
                source_tier=SourceTier.VERIFIED,
                text=correction.proposed_value,
                citations=[correction_citation(correction, source_tier=SourceTier.VERIFIED)],
                score=1000.0,
                title="Verified correction",
                created_at=correction.reviewed_at or correction.created_at,
            )
        )
    return items


def _tracked_state_evidence(session: Session, *, space_id: UUID, query_text: str) -> list[ChatEvidenceItem]:
    repo = TrackedStateRepository(session)
    terms = _query_terms(query_text)
    items: list[ChatEvidenceItem] = []
    for index, field in enumerate(repo.list_active_fields_for_space(space_id), start=1):
        current_value = repo.get_current_value(field.id)
        if current_value is None:
            continue
        citations = [
            citation
            for citation in (_citation_from_raw(raw) for raw in current_value.citations or [])
            if citation is not None
        ]
        text = f"{field.label}: {current_value.value_text}"
        searchable = " ".join([field.key, field.label, field.prompt, current_value.value_text])
        items.append(
            ChatEvidenceItem(
                id=f"tracked-{index}",
                source_type="tracked_state",
                source_tier=SourceTier(current_value.source_tier),
                text=text,
                citations=citations,
                score=800.0 + _overlap_score(terms, searchable),
                title=field.label,
                created_at=current_value.created_at,
            )
        )
    return items


def _search_result_evidence(results: list[SearchResult]) -> list[ChatEvidenceItem]:
    items: list[ChatEvidenceItem] = []
    for index, result in enumerate(results, start=1):
        if result.result_kind == "document_chunk":
            source_type = "document_chunk"
            source_tier = SourceTier.DOCUMENT
            title = result.document.title if result.document is not None else None
            text = result.preview_text.strip()
            created_at = result.document.created_at if result.document is not None else None
        elif result.entity is not None:
            source_type = "graph_entity"
            source_tier = SourceTier.DERIVED
            title = result.entity.display_name
            text = result.preview_text.strip() or result.entity.display_name
            created_at = result.document.created_at if result.document is not None else None
        else:
            continue
        if not text:
            continue
        items.append(
            ChatEvidenceItem(
                id=f"retrieval-{index}",
                source_type=source_type,
                source_tier=source_tier,
                text=text,
                citations=result.citations,
                score=float(result.score),
                title=title,
                created_at=created_at,
            )
        )
    return items


def _graph_relationship_evidence(session: Session, *, document_id: UUID | None) -> list[ChatEvidenceItem]:
    if document_id is None:
        return []

    items: list[ChatEvidenceItem] = []
    for index, record in enumerate(KnowledgeGraphRepository(session).list_edges_for_document(document_id, limit=8), start=1):
        if record.document.deleted_at is not None:
            continue
        relation = record.edge.relation_type.replace("_", " ")
        text = f"{record.source_entity.display_name} {relation} {record.target_entity.display_name}"
        items.append(
            ChatEvidenceItem(
                id=f"graph-{index}",
                source_type="graph_relationship",
                source_tier=SourceTier.DERIVED,
                text=text,
                citations=[
                    Citation(
                        document_id=record.document.id,
                        entity_id=record.source_entity.id,
                        chunk_id=str(record.edge.chunk_id),
                        title=record.document.title,
                        locator=record.edge.provenance_locator,
                        source_tier=SourceTier.DERIVED,
                    )
                ],
                score=350.0 + float(record.edge.weight),
                title=record.document.title,
                created_at=record.document.created_at,
            )
        )
    return items


def _history_items(messages: list[ChatMessage]) -> list[ChatHistoryItem]:
    relevant_messages = [
        message
        for message in messages
        if message.role in {"user", "assistant"} and message.content.strip()
    ][-HISTORY_MESSAGE_LIMIT:]
    return [
        ChatHistoryItem(role=message.role, content=message.content, created_at=message.created_at)
        for message in relevant_messages
    ]


def gather_chat_evidence(
    session: Session,
    subject: str,
    chat_session: ChatSession,
    *,
    query_text: str,
    prior_messages: list[ChatMessage],
) -> ChatEvidenceBundle:
    retrieval_results = retrieve_search_results(
        session,
        subject,
        space_scope=SpaceScope(space_id=chat_session.space_id),
        query_text=query_text,
        mode=SearchMode.COMBINED,
        document_id=chat_session.document_id,
        limit=12,
    )

    evidence_items = [
        *_correction_evidence(session, space_id=chat_session.space_id, query_text=query_text),
        *_tracked_state_evidence(session, space_id=chat_session.space_id, query_text=query_text),
        *_search_result_evidence(retrieval_results),
        *_graph_relationship_evidence(session, document_id=chat_session.document_id),
    ]
    return ChatEvidenceBundle(
        evidence_items=_dedupe_and_rank(evidence_items),
        history_items=_history_items(prior_messages),
        retrieval_results=retrieval_results,
    )
