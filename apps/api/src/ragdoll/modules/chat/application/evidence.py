from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import Citation, SourceTier, SpaceScope
from ragdoll.modules.corrections.application.service import correction_citation, correction_matches_query
from ragdoll.modules.corrections.infrastructure.repository import CorrectionsRepository
from ragdoll.modules.knowledge_graph.infrastructure.repository import KnowledgeGraphRepository
from ragdoll.modules.search.api.schemas import SearchMode, SearchResult
from ragdoll.modules.search.application.evidence import retrieve_search_results
from ragdoll.modules.tracked_state.infrastructure.repository import TrackedStateRepository
from ragdoll.platform.db.models import ChatMessage, ChatSession, Document, DocumentChunk


SOURCE_QUOTAS = {
    "correction": 3,
    "tracked_state": 5,
    "document_chunk": 8,
    "graph_entity": 4,
    "graph_relationship": 6,
}
TOTAL_EVIDENCE_LIMIT = 16
HISTORY_MESSAGE_LIMIT = 8
EXPANDED_DOCUMENT_EVIDENCE_MAX_CHARS = 4200

TECH_STACK_QUERY_PHRASES = (
    "programming language",
    "programming languages",
    "tech stack",
    "technical stack",
    "technology stack",
)
TECH_STACK_SECTION_RE = re.compile(
    r"(?im)^#{1,6}\s+.*(?:tech|technical|technology)\s+stack\b.*$"
)
TECH_STACK_TABLE_RE = re.compile(
    r"(?im)^\s*\|\s*component\s*\|\s*technology\s*\|"
)
TECH_STACK_EVIDENCE_TERMS = (
    "backend service",
    "backend framework",
    "frontend",
    "frontend build",
    "desktop app",
    "ai service",
    "ai framework",
    "database",
    "ml framework",
    "packaging",
    "programming language",
)
TECH_STACK_NOISE_PATTERNS = (
    r"\bc:\\",
    r"\bprogram files\b",
    r"\bappdata\b",
    r"\blocalhost:\d+\b",
    r"\bipcmain\b",
    r"\belectron-updater\b",
    r"\bstart-drag\b",
    r"\bimage_(?:updated|deleted|renamed)\b",
    r"\bdocker\b.*\bbinds\b",
    r"\bgetcontainer\b",
)


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
    answer_intent: str = "general"
    answerability: float = 0.0


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


def classify_answer_intent(query_text: str) -> str:
    normalized = _normalized_text(query_text)
    terms = _query_terms(query_text)
    if (
        any(phrase in normalized for phrase in TECH_STACK_QUERY_PHRASES)
        or {"tech", "stack"}.issubset(terms)
        or {"technology", "stack"}.issubset(terms)
        or ("programming" in terms and {"language", "languages"}.intersection(terms))
    ):
        return "technology_stack"
    if any(
        phrase in normalized
        for phrase in (
            "related to",
            "relationship between",
            "relationships between",
            "connected to",
            "connections between",
        )
    ) or any(
        term in terms
        for term in ("graph", "relationship", "relationships", "related", "connect", "connected", "network", "link")
    ):
        return "relationship"
    if any(
        normalized.startswith(prefix)
        for prefix in (
            "tell me about",
            "what is",
            "who is",
            "summarize",
            "summary of",
            "describe",
            "give me an overview of",
            "overview of",
        )
    ):
        return "summary"
    return "general"


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


def _tier_rank(source_tier: SourceTier) -> int:
    return {
        SourceTier.VERIFIED: 4,
        SourceTier.USER: 3,
        SourceTier.DOCUMENT: 2,
        SourceTier.DERIVED: 1,
    }.get(source_tier, 0)


def _dedupe_and_rank(items: list[ChatEvidenceItem]) -> list[ChatEvidenceItem]:
    unique: dict[tuple[str, tuple[tuple[object, ...], ...]], ChatEvidenceItem] = {}
    for item in items:
        key = (_normalized_text(item.text), tuple(_citation_key(citation) for citation in item.citations))
        existing = unique.get(key)
        if existing is None or (item.answerability, item.score) > (existing.answerability, existing.score):
            unique[key] = item

    by_source: dict[str, list[ChatEvidenceItem]] = {}
    for item in sorted(unique.values(), key=lambda value: (value.answerability, value.score), reverse=True):
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
            item.answerability,
            _tier_rank(item.source_tier),
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
                answer_intent=classify_answer_intent(query_text),
                answerability=1000.0,
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
                answer_intent=classify_answer_intent(query_text),
                answerability=800.0 + _overlap_score(terms, searchable),
            )
        )
    return items


def _parse_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _result_chunk_id(result: SearchResult) -> UUID | None:
    if result.result_kind == "document_chunk":
        parsed = _parse_uuid(result.result_id)
        if parsed is not None:
            return parsed
    for citation in result.citations:
        parsed = _parse_uuid(citation.chunk_id)
        if parsed is not None:
            return parsed
    return None


def _compact_evidence_text(value: str, *, max_chars: int = EXPANDED_DOCUMENT_EVIDENCE_MAX_CHARS) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n").strip()
    if len(normalized) <= max_chars:
        return normalized
    clipped = normalized[:max_chars].rsplit("\n", 1)[0].strip()
    return f"{clipped}\n..."


def _heading_level(line: str) -> int | None:
    match = re.match(r"^(#{1,6})\s+\S", line)
    if match is None:
        return None
    return len(match.group(1))


def _extract_heading_section(text: str, heading_matcher: re.Pattern[str]) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    for start_index, line in enumerate(lines):
        if heading_matcher.search(line) is None:
            continue
        level = _heading_level(line) or 6
        end_index = len(lines)
        for next_index in range(start_index + 1, len(lines)):
            next_level = _heading_level(lines[next_index])
            if next_level is not None and next_level <= level:
                end_index = next_index
                break
        return "\n".join(lines[start_index:end_index]).strip()
    return ""


def _extract_stack_table(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    for start_index, line in enumerate(lines):
        if TECH_STACK_TABLE_RE.search(line) is None:
            continue
        end_index = start_index
        while end_index < len(lines) and lines[end_index].strip().startswith("|"):
            end_index += 1
        return "\n".join(lines[start_index:end_index]).strip()
    return ""


def _extract_relevant_markdown_context(text: str, *, answer_intent: str) -> str:
    if answer_intent == "technology_stack":
        section = _extract_heading_section(text, TECH_STACK_SECTION_RE)
        if section:
            return section
        table = _extract_stack_table(text)
        if table:
            return table
    if answer_intent == "summary":
        section = _extract_heading_section(
            text,
            re.compile(r"(?im)^#{1,6}\s+(?:executive summary|summary|overview)\b.*$"),
        )
        if section:
            return section
    return ""


def _document_context_by_chunk_id(
    session: Session,
    results: list[SearchResult],
    *,
    answer_intent: str,
) -> dict[UUID, str]:
    hit_ids = [chunk_id for result in results if (chunk_id := _result_chunk_id(result)) is not None]
    if not hit_ids:
        return {}

    hit_chunks = session.execute(
        select(DocumentChunk).where(DocumentChunk.id.in_(hit_ids))
    ).scalars().all()
    hit_by_id = {chunk.id: chunk for chunk in hit_chunks}
    document_ids = list({chunk.document_id for chunk in hit_chunks})
    section_by_document: dict[UUID, str] = {}
    if answer_intent in {"technology_stack", "summary"} and document_ids:
        documents = session.execute(select(Document).where(Document.id.in_(document_ids))).scalars().all()
        for document in documents:
            document_text = document.original_text_content or ""
            relevant_context = _extract_relevant_markdown_context(document_text, answer_intent=answer_intent)
            if relevant_context:
                section_by_document[document.id] = _compact_evidence_text(relevant_context)

    chunks_by_document: dict[UUID, list[DocumentChunk]] = {}
    if answer_intent in {"technology_stack", "summary"} and document_ids:
        document_chunks = session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id.in_(document_ids))
            .order_by(DocumentChunk.document_id.asc(), DocumentChunk.chunk_index.asc())
        ).scalars().all()
        for chunk in document_chunks:
            chunks_by_document.setdefault(chunk.document_id, []).append(chunk)

    context_by_id: dict[UUID, str] = {}
    for chunk_id, chunk in hit_by_id.items():
        if chunk.document_id in section_by_document:
            context_by_id[chunk_id] = section_by_document[chunk.document_id]
            continue
        related_chunks = chunks_by_document.get(chunk.document_id)
        if related_chunks:
            nearby = [
                candidate
                for candidate in related_chunks
                if abs(candidate.chunk_index - chunk.chunk_index) <= 1
            ]
            combined = "\n\n".join(candidate.text_content for candidate in nearby)
        else:
            combined = chunk.text_content
        relevant_context = _extract_relevant_markdown_context(combined, answer_intent=answer_intent)
        context_by_id[chunk_id] = _compact_evidence_text(relevant_context or chunk.text_content)
    return context_by_id


def _technology_stack_answerability(text: str, query_terms: set[str]) -> float:
    lower = text.lower()
    score = _overlap_score(query_terms, text)
    if TECH_STACK_SECTION_RE.search(text):
        score += 90.0
    if TECH_STACK_TABLE_RE.search(text):
        score += 80.0
    evidence_hits = sum(1 for term in TECH_STACK_EVIDENCE_TERMS if term in lower)
    score += min(evidence_hits, 8) * 9.0
    if re.search(r"(?im)^\s*[-*]\s+\*\*[^*]+\*\*\s*:", text):
        score += 30.0
    if "```" in text and not TECH_STACK_SECTION_RE.search(text):
        score -= 45.0
    if any(char in text for char in "┌┐└┘├┤│─"):
        score -= 70.0
    if re.search(r"(?s)\{\s*\"type\"\s*:\s*\"[^\"]+\"", text):
        score -= 70.0
    if any(re.search(pattern, lower) for pattern in TECH_STACK_NOISE_PATTERNS) and not TECH_STACK_SECTION_RE.search(text):
        score -= 60.0
    return score


def _answerability_score(
    *,
    answer_intent: str,
    source_type: str,
    text: str,
    query_terms: set[str],
) -> float:
    if source_type == "correction":
        return 1000.0 + _overlap_score(query_terms, text)
    if source_type == "tracked_state":
        return 800.0 + _overlap_score(query_terms, text)
    if answer_intent == "technology_stack" and source_type == "document_chunk":
        return _technology_stack_answerability(text, query_terms)
    if answer_intent == "summary" and source_type == "document_chunk":
        score = _overlap_score(query_terms, text)
        if re.search(r"(?im)^#{1,6}\s+(?:executive summary|summary|overview)\b", text):
            score += 70.0
        return score
    if answer_intent == "relationship" and source_type in {"graph_entity", "graph_relationship"}:
        return 60.0 + _overlap_score(query_terms, text)
    return _overlap_score(query_terms, text)


def _search_result_evidence(
    session: Session,
    results: list[SearchResult],
    *,
    query_text: str,
    answer_intent: str,
) -> list[ChatEvidenceItem]:
    terms = _query_terms(query_text)
    context_by_chunk_id = _document_context_by_chunk_id(session, results, answer_intent=answer_intent)
    items: list[ChatEvidenceItem] = []
    for index, result in enumerate(results, start=1):
        if result.result_kind == "document_chunk":
            source_type = "document_chunk"
            source_tier = SourceTier.DOCUMENT
            title = result.document.title if result.document is not None else None
            chunk_id = _result_chunk_id(result)
            text = (context_by_chunk_id.get(chunk_id) if chunk_id is not None else None) or result.preview_text.strip()
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
        answerability = _answerability_score(
            answer_intent=answer_intent,
            source_type=source_type,
            text=text,
            query_terms=terms,
        )
        items.append(
            ChatEvidenceItem(
                id=f"retrieval-{index}",
                source_type=source_type,
                source_tier=source_tier,
                text=text,
                citations=result.citations,
                score=float(result.score) + answerability,
                title=title,
                created_at=created_at,
                answer_intent=answer_intent,
                answerability=answerability,
            )
        )
    return items


def _graph_relationship_evidence(
    session: Session,
    *,
    document_id: UUID | None,
    query_text: str,
    answer_intent: str,
) -> list[ChatEvidenceItem]:
    if document_id is None:
        return []

    terms = _query_terms(query_text)
    items: list[ChatEvidenceItem] = []
    for index, record in enumerate(KnowledgeGraphRepository(session).list_edges_for_document(document_id, limit=8), start=1):
        if record.document.deleted_at is not None:
            continue
        relation = record.edge.relation_type.replace("_", " ")
        text = f"{record.source_entity.display_name} {relation} {record.target_entity.display_name}"
        answerability = _answerability_score(
            answer_intent=answer_intent,
            source_type="graph_relationship",
            text=text,
            query_terms=terms,
        )
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
                score=350.0 + float(record.edge.weight) + answerability,
                title=record.document.title,
                created_at=record.document.created_at,
                answer_intent=answer_intent,
                answerability=answerability,
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
    answer_intent = classify_answer_intent(query_text)
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
        *_search_result_evidence(session, retrieval_results, query_text=query_text, answer_intent=answer_intent),
        *_graph_relationship_evidence(
            session,
            document_id=chat_session.document_id,
            query_text=query_text,
            answer_intent=answer_intent,
        ),
    ]
    return ChatEvidenceBundle(
        evidence_items=_dedupe_and_rank(evidence_items),
        history_items=_history_items(prior_messages),
        retrieval_results=retrieval_results,
    )
