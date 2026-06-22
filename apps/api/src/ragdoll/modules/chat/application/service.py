from __future__ import annotations

from typing import Iterable
from uuid import UUID

from ragdoll.api.shared_schemas import Citation, SourceTier
from ragdoll.modules.chat.api.schemas import ChatMessageRecord, ChatSessionDetail, ChatSessionSummary, ChatSuggestion
from ragdoll.modules.corrections.application.service import correction_citation, correction_matches_query
from ragdoll.modules.corrections.infrastructure.repository import CorrectionsRepository
from ragdoll.modules.search.api.schemas import SearchMode, SearchResult
from ragdoll.platform.db.models import ChatMessage, ChatSession


def _truncate_title(value: str) -> str:
    title = " ".join(value.strip().split())
    return title[:80] or "New chat"


def _message_citations(message: ChatMessage) -> list[Citation]:
    return [Citation.model_validate(item) for item in (message.citations or [])]


def _message_suggestions(message: ChatMessage) -> list[ChatSuggestion]:
    return [ChatSuggestion.model_validate(item) for item in (message.suggestions or [])]


def build_chat_message_record(message: ChatMessage) -> ChatMessageRecord:
    return ChatMessageRecord(
        id=message.id,
        role=message.role,
        content=message.content,
        citations=_message_citations(message),
        suggestions=_message_suggestions(message),
        retrieval_mode=message.retrieval_mode,
        degraded=message.degraded,
        created_at=message.created_at,
    )


def build_chat_session_summary(chat_session: ChatSession) -> ChatSessionSummary:
    last_message = chat_session.messages[-1] if chat_session.messages else None
    return ChatSessionSummary(
        id=chat_session.id,
        space_id=chat_session.space_id,
        title=chat_session.title,
        message_count=len(chat_session.messages),
        last_message_at=last_message.created_at if last_message is not None else None,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at,
    )


def build_chat_session_detail(chat_session: ChatSession) -> ChatSessionDetail:
    return ChatSessionDetail(
        **build_chat_session_summary(chat_session).model_dump(),
        messages=[build_chat_message_record(message) for message in chat_session.messages],
    )


def build_chat_suggestions(results: list[SearchResult]) -> list[ChatSuggestion]:
    suggestions: list[ChatSuggestion] = []
    for result in results[:3]:
        if result.entity is not None:
            label = f"Explore {result.entity.display_name}"
            prompt = f"What should I know about {result.entity.display_name}?"
        else:
            label = f"Open {result.document.title if result.document else 'document'}"
            prompt = f"Summarize {result.document.title if result.document else 'this result'}."
        suggestions.append(ChatSuggestion(label=label[:80], prompt=prompt[:200]))
    return suggestions


def collect_verified_corrections(session, *, space_id: UUID, query_text: str):
    repo = CorrectionsRepository(session)
    return [row for row in repo.list_verified_for_space(space_id) if correction_matches_query(row, query_text)]


def _dedupe_citations(citations: Iterable[Citation]) -> list[Citation]:
    unique: dict[tuple[object, ...], Citation] = {}
    for citation in citations:
        key = (citation.document_id, citation.entity_id, citation.chunk_id, citation.locator, citation.source_tier)
        unique.setdefault(key, citation)
    return list(unique.values())


def compose_fallback_answer(
    *,
    query_text: str,
    retrieval_results: list[SearchResult],
    verified_corrections,
) -> tuple[str, list[Citation], list[ChatSuggestion]]:
    verified_bits = [correction.proposed_value for correction in verified_corrections[:2]]
    evidence_bits: list[str] = []
    citations: list[Citation] = []

    for correction in verified_corrections[:3]:
        citations.append(correction_citation(correction, source_tier=SourceTier.VERIFIED))

    for result in retrieval_results[:3]:
        citations.extend(result.citations)
        if result.entity is not None:
            evidence_bits.append(result.entity.display_name)
        elif result.document is not None:
            evidence_bits.append(f"{result.document.title}: {result.preview_text}")
        else:
            evidence_bits.append(result.preview_text)

    if verified_bits and evidence_bits:
        answer = (
            f"Verified correction(s) for '{query_text}': {', '.join(verified_bits)}. "
            f"Related evidence: {' | '.join(evidence_bits[:2])}."
        )
    elif verified_bits:
        answer = f"Verified correction(s) for '{query_text}': {', '.join(verified_bits)}."
    elif evidence_bits:
        answer = f"Current evidence for '{query_text}': {' | '.join(evidence_bits[:2])}."
    else:
        answer = f"No scoped evidence was found for '{query_text}'."

    return answer[:2000], _dedupe_citations(citations)[:8], build_chat_suggestions(retrieval_results)
