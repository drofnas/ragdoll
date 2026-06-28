from __future__ import annotations

import re
from typing import Iterable
from uuid import UUID

from ragdoll.api.shared_schemas import Citation, SourceTier
from ragdoll.modules.chat.api.schemas import (
    ChatEvidenceRecord,
    ChatMessageRecord,
    ChatSessionDetail,
    ChatSessionSummary,
    ChatSuggestion,
)
from ragdoll.modules.chat.application.evidence import ChatEvidenceItem, ChatHistoryItem, classify_answer_intent
from ragdoll.modules.corrections.application.service import correction_citation, correction_matches_query
from ragdoll.modules.corrections.infrastructure.repository import CorrectionsRepository
from ragdoll.modules.search.api.schemas import SearchMode, SearchResult
from ragdoll.platform.llm import ChatCompletionMessage
from ragdoll.platform.db.models import ChatMessage, ChatSession


CHAT_EVIDENCE_PROMPT_BUDGET = 6500
CHAT_HISTORY_PROMPT_BUDGET = 2000


def _truncate_title(value: str) -> str:
    title = " ".join(value.strip().split())
    return title[:80] or "New chat"


def _message_citations(message: ChatMessage) -> list[Citation]:
    return [Citation.model_validate(item) for item in (message.citations or [])]


def _message_suggestions(message: ChatMessage) -> list[ChatSuggestion]:
    return [ChatSuggestion.model_validate(item) for item in (message.suggestions or [])]


def _message_evidence(message: ChatMessage) -> list[ChatEvidenceRecord]:
    return [ChatEvidenceRecord.model_validate(item) for item in (message.evidence or [])]


def build_chat_message_record(message: ChatMessage) -> ChatMessageRecord:
    return ChatMessageRecord(
        id=message.id,
        role=message.role,
        content=message.content,
        citations=_message_citations(message),
        suggestions=_message_suggestions(message),
        evidence=_message_evidence(message),
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
        key = (
            citation.document_id,
            citation.entity_id,
            citation.chunk_id,
            citation.locator,
            citation.line_number,
            citation.source_tier,
        )
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


def _clean_markdown_cell(value: str) -> str:
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    cleaned = re.sub(r"`+", "", cleaned)
    cleaned = re.sub(r"\*\*([^*]+)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"<br\s*/?>", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip(" -")


def _clean_prompt_fragment(value: str, *, max_chars: int = 1200) -> str:
    return re.sub(r"\s+", " ", value).strip()[:max_chars]


def _answerability_label(value: float) -> str:
    if value >= 75:
        return "high"
    if value >= 20:
        return "medium"
    return "low"


def _prompt_fragment_limit(item: ChatEvidenceItem) -> int:
    if item.answerability >= 75:
        return 1800
    if item.answerability >= 20:
        return 900
    return 300


def _bounded_lines(lines: list[str], *, max_chars: int) -> str:
    selected: list[str] = []
    used = 0
    for line in lines:
        budget_left = max_chars - used
        if budget_left <= 0:
            break
        if len(line) > budget_left:
            clipped = line[: max(0, budget_left - 4)].rstrip()
            if clipped:
                selected.append(f"{clipped} ...")
            break
        selected.append(line)
        used += len(line) + 1
    return "\n".join(selected)


def build_evidence_records(evidence_items: list[ChatEvidenceItem]) -> list[ChatEvidenceRecord]:
    return [
        ChatEvidenceRecord(
            id=item.id,
            source_type=item.source_type,
            source_tier=item.source_tier,
            text=item.text,
            citations=item.citations,
            score=item.score,
            title=item.title,
            created_at=item.created_at,
        )
        for item in evidence_items
    ]


def build_synthesis_messages(
    *,
    query_text: str,
    evidence_items: list[ChatEvidenceItem],
    history_items: list[ChatHistoryItem],
) -> list[ChatCompletionMessage]:
    system_prompt = (
        "You are Ragdoll's evidence-grounded chat assistant. Answer the latest user question using only the "
        "provided evidence. Use chat history only to resolve references and follow-up context; do not treat "
        "chat history as authoritative factual evidence. Obey requested formatting such as bullets or tables. "
        "Cite supporting evidence inline with IDs like [E1]. If evidence conflicts, say what conflicts. If the "
        "evidence is insufficient, say what is missing. Prefer high-answerability evidence. Treat low-answerability "
        "evidence as possible noise, especially raw code, JSON events, diagrams, installation paths, Docker snippets, "
        "and localhost wiring unless the user directly asks for those details. Answer directly and concisely."
    )
    history_lines = [
        f"- {item.role}: {_clean_prompt_fragment(item.content, max_chars=350)}"
        for item in history_items[-4:]
    ]
    history_block = _bounded_lines(history_lines, max_chars=CHAT_HISTORY_PROMPT_BUDGET) or "None"
    evidence_lines = [
        (
            f"[{item.id}] source={item.source_type}; tier={item.source_tier.value}; "
            f"intent={item.answer_intent}; answerability={_answerability_label(item.answerability)}; "
            f"title={item.title or 'untitled'}; "
            f"text={_clean_prompt_fragment(item.text, max_chars=_prompt_fragment_limit(item))}"
        )
        for item in evidence_items
    ]
    evidence_block = _bounded_lines(evidence_lines, max_chars=CHAT_EVIDENCE_PROMPT_BUDGET) or "None"
    user_prompt = (
        f"Recent chat history:\n{history_block}\n\n"
        f"Evidence packet:\n{evidence_block}\n\n"
        f"Question:\n{query_text}\n\n"
        "Write the final answer now. Include evidence IDs next to claims."
    )
    return [
        ChatCompletionMessage(role="system", content=system_prompt),
        ChatCompletionMessage(role="user", content=user_prompt),
    ]


def _split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return []
    return [_clean_markdown_cell(cell) for cell in stripped.strip("|").split("|")]


def _is_markdown_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def _looks_like_technology_stack_row(component: str, technology: str) -> bool:
    component_terms = (
        "app",
        "backend",
        "build",
        "database",
        "desktop",
        "framework",
        "frontend",
        "hashing",
        "image",
        "management",
        "model",
        "packaging",
        "parsing",
        "processing",
        "scroll",
        "service",
        "watching",
        "xmp",
    )
    technology_terms = (
        "+",
        "electron",
        "echo",
        "fastapi",
        "fiber",
        "florence",
        "go ",
        "python",
        "pytorch",
        "sqlite",
        "svelte",
        "transformers",
        "uvicorn",
        "vite",
    )
    normalized_component = component.lower()
    normalized_technology = technology.lower()
    return any(term in normalized_component for term in component_terms) and any(
        term in normalized_technology for term in technology_terms
    )


def _column_index(headers: list[str], candidates: tuple[str, ...]) -> int | None:
    normalized_headers = [header.lower() for header in headers]
    for candidate in candidates:
        for index, header in enumerate(normalized_headers):
            if candidate in header:
                return index
    return None


def _tech_stack_table_rows(item: ChatEvidenceItem) -> list[tuple[str, str, str]]:
    lines = item.text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
    rows: list[tuple[str, str, str]] = []
    for index, line in enumerate(lines):
        headers = _split_markdown_row(line)
        if not headers:
            continue
        component_index = _column_index(headers, ("component", "area", "part"))
        technology_index = _column_index(headers, ("technology", "tech", "language", "framework"))
        if component_index is None or technology_index is None:
            continue
        next_index = index + 1
        if next_index < len(lines):
            separator_cells = _split_markdown_row(lines[next_index])
            if _is_markdown_separator_row(separator_cells):
                next_index += 1
        for table_line in lines[next_index:]:
            cells = _split_markdown_row(table_line)
            if not cells:
                break
            if _is_markdown_separator_row(cells):
                continue
            if max(component_index, technology_index) >= len(cells):
                continue
            component = cells[component_index]
            technology = cells[technology_index]
            if component and technology:
                rows.append((component, technology, item.id))
    return rows


def _tech_stack_loose_table_rows(item: ChatEvidenceItem) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in item.text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        cells = _split_markdown_row(line)
        if len(cells) < 2 or _is_markdown_separator_row(cells):
            continue
        component = cells[0]
        technology = cells[1]
        if _looks_like_technology_stack_row(component, technology):
            rows.append((component, technology, item.id))
    return rows


def _tech_stack_list_rows(item: ChatEvidenceItem) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for line in item.text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        match = re.match(r"^\s*(?:[-*]|\d+\.)\s+\*\*([^*]+)\*\*\s*(?:\(([^)]*)\))?\s*:?\s*(.*)$", line)
        if match is None:
            continue
        label = _clean_markdown_cell(match.group(1))
        inline_value = _clean_markdown_cell(match.group(2) or "")
        description = _clean_markdown_cell(match.group(3) or "")
        technology = inline_value or description
        if label and technology:
            rows.append((label, technology, item.id))
    return rows


def _compose_technology_stack_fallback(evidence_items: list[ChatEvidenceItem]) -> str | None:
    candidate_items = [
        item
        for item in evidence_items
        if item.source_type == "document_chunk" and item.answerability >= 55
    ]
    rows: list[tuple[str, str, str]] = []
    for item in candidate_items:
        rows.extend(_tech_stack_table_rows(item))
    if not rows:
        for item in candidate_items:
            rows.extend(_tech_stack_loose_table_rows(item))
    if not rows:
        for item in candidate_items:
            rows.extend(_tech_stack_list_rows(item))
    if not rows:
        return None

    seen: set[tuple[str, str]] = set()
    lines = ["Based on the Technology Stack evidence:"]
    for component, technology, evidence_id in rows:
        key = (component.lower(), technology.lower())
        if key in seen:
            continue
        seen.add(key)
        lines.append(f"- {component}: {technology} [{evidence_id}]")
        if len(lines) >= 21:
            break
    return "\n".join(lines)


def _insufficient_degraded_answer(query_text: str) -> str:
    return (
        "I could not produce a reliable answer from the available evidence while the chat model was unavailable. "
        f"The retrieved evidence was insufficient or too noisy for: '{query_text}'."
    )


def compose_deterministic_evidence_answer(
    *,
    query_text: str,
    evidence_items: list[ChatEvidenceItem],
) -> str:
    if not evidence_items:
        return f"No scoped evidence was found for '{query_text}'."

    correction_items = [item for item in evidence_items if item.source_type == "correction"]
    if correction_items:
        return " ".join(
            f"Verified correction: {_clean_summary_fragment(item.text)} [{item.id}]."
            for item in correction_items[:2]
        )

    if classify_answer_intent(query_text) == "technology_stack":
        stack_answer = _compose_technology_stack_fallback(evidence_items)
        if stack_answer is not None:
            return stack_answer
        return _insufficient_degraded_answer(query_text)

    selected_items = [item for item in evidence_items if item.answerability >= 0][:1]
    if not selected_items:
        return _insufficient_degraded_answer(query_text)
    return "Based on the available evidence: " + " ".join(
        f"{_clean_summary_fragment(item.text)} [{item.id}]."
        for item in selected_items
    )


def _answer_declares_insufficient_evidence(answer_text: str) -> bool:
    normalized = _normalized_text(answer_text)
    return (
        "could not produce a reliable answer" in normalized
        or "insufficient" in normalized
        or "no scoped evidence was found" in normalized
    )


def citations_for_synthesized_answer(answer_text: str, evidence_items: list[ChatEvidenceItem]) -> list[Citation]:
    cited_ids = set(re.findall(r"\[(E\d+)\]", answer_text))
    selected_items = [
        item
        for item in evidence_items
        if item.id in cited_ids
    ]
    if not selected_items and _answer_declares_insufficient_evidence(answer_text):
        return []
    if not selected_items:
        selected_items = evidence_items[:3]
    citations: list[Citation] = []
    for item in selected_items:
        citations.extend(item.citations)
    return _dedupe_citations(citations)[:8]


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
    document_citations: list[Citation] = []
    entity_citations: list[Citation] = []
    seen_document_ids: set[UUID] = set()
    summary_bias = _is_summary_question(query_text) and not _is_graph_or_relation_question(query_text)

    for correction in verified_corrections[:3]:
        citations.append(correction_citation(correction, source_tier=SourceTier.VERIFIED))

    for result in prioritized_results[:3]:
        if result.result_kind == "document_chunk":
            if result.document is not None:
                if result.document.id not in seen_document_ids:
                    seen_document_ids.add(result.document.id)
                    document_citations.extend(result.citations)
                    context_text = (document_context or {}).get(result.document.id, "")
                    if summary_bias and context_text:
                        document_bits.append(
                            f"{result.document.title}: {_extract_document_summary(context_text)}"
                        )
                    else:
                        document_bits.append(f"{result.document.title}: {_clean_summary_fragment(result.preview_text)}")
            else:
                document_citations.extend(result.citations)
                document_bits.append(_clean_summary_fragment(result.preview_text))
            continue
        if result.entity is not None:
            entity_citations.extend(result.citations)
            entity_bits.append(result.entity.display_name)
        elif result.preview_text:
            entity_citations.extend(result.citations)
            entity_bits.append(_clean_summary_fragment(result.preview_text))

    evidence_bits = document_bits or entity_bits
    citations.extend(document_citations if document_bits else entity_citations)

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
