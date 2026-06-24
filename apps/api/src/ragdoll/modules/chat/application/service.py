from __future__ import annotations

import re
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
        document_id=chat_session.document_id,
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


def _normalized_text(value: str) -> str:
    return " ".join(value.lower().split())


def _is_graph_or_relation_question(query_text: str) -> bool:
    normalized = _normalized_text(query_text)
    graph_phrases = (
        "related to",
        "relationship between",
        "relationships between",
        "connected to",
        "connections between",
    )
    graph_terms = {"graph", "relationship", "relationships", "related", "connect", "connected", "network", "link"}
    return any(phrase in normalized for phrase in graph_phrases) or any(
        term in normalized.split() for term in graph_terms
    )


def _is_summary_question(query_text: str) -> bool:
    normalized = _normalized_text(query_text)
    summary_prefixes = (
        "tell me about",
        "what is",
        "who is",
        "summarize",
        "summary of",
        "describe",
        "give me an overview of",
        "overview of",
    )
    return any(normalized.startswith(prefix) for prefix in summary_prefixes)


def _chunk_position(result: SearchResult) -> int | None:
    for citation in result.citations:
        locator = citation.locator or ""
        match = re.fullmatch(r"chunk:(\d+)", locator)
        if match is not None:
            return int(match.group(1))
    return None


def _early_chunk_bonus(result: SearchResult) -> int:
    chunk_position = _chunk_position(result)
    if chunk_position is None:
        return 0
    return max(0, 1000 - chunk_position)


def _prioritize_chat_results(
    query_text: str,
    retrieval_results: list[SearchResult],
    *,
    document_id: UUID | None,
) -> list[SearchResult]:
    if not retrieval_results:
        return []

    summary_bias = _is_summary_question(query_text) and not _is_graph_or_relation_question(query_text)

    def rank_key(result: SearchResult) -> tuple[int, int, int, int, float]:
        same_document = int(
            document_id is not None
            and result.document is not None
            and result.document.id == document_id
        )
        document_chunk = int(result.result_kind == "document_chunk")
        return (
            same_document,
            document_chunk if summary_bias else 0,
            int(SearchMode.BOOLEAN in result.matched_modes),
            _early_chunk_bonus(result) if summary_bias else 0,
            result.score,
        )

    return sorted(retrieval_results, key=rank_key, reverse=True)


def _clean_summary_fragment(value: str) -> str:
    cleaned = re.sub(r"`+", "", value)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"#+\s*", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -|:")


def _extract_document_summary(document_text: str) -> str:
    normalized = document_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""

    summary_match = re.search(
        r"(?ims)^##?\s*(executive summary|summary|overview)\s*$\n(.*?)(?=^##?\s+\S|\Z)",
        normalized,
    )
    if summary_match is not None:
        section_body = summary_match.group(2).strip()
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", section_body) if part.strip()]
        candidate = " ".join(paragraphs[:2])
        if candidate:
            return _clean_summary_fragment(candidate[:500])

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", normalized) if part.strip()]
    content_paragraphs = [
        paragraph
        for paragraph in paragraphs
        if not paragraph.startswith("#") and len(paragraph.split()) >= 8
    ]
    if content_paragraphs:
        return _clean_summary_fragment(" ".join(content_paragraphs[:2])[:500])
    return _clean_summary_fragment(normalized[:500])


def _strip_document_label(value: str) -> str:
    return re.sub(r"^[^:]+:\s*", "", value, count=1).strip()


def compose_fallback_answer(
    *,
    query_text: str,
    retrieval_results: list[SearchResult],
    verified_corrections,
    document_id: UUID | None = None,
    document_context: dict[UUID, str] | None = None,
) -> tuple[str, list[Citation], list[ChatSuggestion]]:
    prioritized_results = _prioritize_chat_results(query_text, retrieval_results, document_id=document_id)
    verified_bits = [correction.proposed_value for correction in verified_corrections[:2]]
    document_bits: list[str] = []
    entity_bits: list[str] = []
    citations: list[Citation] = []
    seen_document_ids: set[UUID] = set()
    summary_bias = _is_summary_question(query_text) and not _is_graph_or_relation_question(query_text)

    for correction in verified_corrections[:3]:
        citations.append(correction_citation(correction, source_tier=SourceTier.VERIFIED))

    for result in prioritized_results[:3]:
        citations.extend(result.citations)
        if result.result_kind == "document_chunk":
            if result.document is not None:
                if result.document.id not in seen_document_ids:
                    seen_document_ids.add(result.document.id)
                    context_text = (document_context or {}).get(result.document.id, "")
                    if summary_bias and context_text:
                        document_bits.append(
                            f"{result.document.title}: {_extract_document_summary(context_text)}"
                        )
                    else:
                        document_bits.append(f"{result.document.title}: {_clean_summary_fragment(result.preview_text)}")
            else:
                document_bits.append(_clean_summary_fragment(result.preview_text))
            continue
        if result.entity is not None:
            entity_bits.append(result.entity.display_name)
        elif result.preview_text:
            entity_bits.append(_clean_summary_fragment(result.preview_text))

    evidence_bits = document_bits or entity_bits

    if verified_bits and evidence_bits:
        answer = (
            f"Verified correction(s) for '{query_text}': {', '.join(verified_bits)}. "
            f"Related evidence: {' | '.join(evidence_bits[:2])}."
        )
    elif verified_bits:
        answer = f"Verified correction(s) for '{query_text}': {', '.join(verified_bits)}."
    elif evidence_bits:
        if summary_bias and document_bits:
            answer = " ".join(_strip_document_label(bit) for bit in document_bits[:2]).strip()
        else:
            answer = f"Current evidence for '{query_text}': {' | '.join(evidence_bits[:2])}."
    else:
        answer = f"No scoped evidence was found for '{query_text}'."

    return answer[:2000], _dedupe_citations(citations)[:8], build_chat_suggestions(prioritized_results)
