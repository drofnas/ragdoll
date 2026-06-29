from __future__ import annotations

import re

from ragdoll.modules.chat.application.evidence import ChatEvidenceItem, ChatHistoryItem
from ragdoll.platform.llm import ChatCompletionMessage

CHAT_EVIDENCE_PROMPT_BUDGET = 6500
CHAT_HISTORY_PROMPT_BUDGET = 2000


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


def render_history_block(history_items: list[ChatHistoryItem]) -> str:
    history_lines = [
        f"- {item.role}: {_clean_prompt_fragment(item.content, max_chars=350)}"
        for item in history_items[-4:]
    ]
    return _bounded_lines(history_lines, max_chars=CHAT_HISTORY_PROMPT_BUDGET) or "None"


def render_evidence_block(
    evidence_items: list[ChatEvidenceItem],
    *,
    max_chars: int = CHAT_EVIDENCE_PROMPT_BUDGET,
) -> str:
    evidence_lines = [
        (
            f"[{item.id}] source={item.source_type}; tier={item.source_tier.value}; "
            f"intent={item.answer_intent}; answerability={_answerability_label(item.answerability)}; "
            f"title={item.title or 'untitled'}; "
            f"text={_clean_prompt_fragment(item.text, max_chars=_prompt_fragment_limit(item))}"
        )
        for item in evidence_items
    ]
    return _bounded_lines(evidence_lines, max_chars=max_chars) or "None"


def build_chat_synthesis_messages(
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
    user_prompt = (
        f"Recent chat history:\n{render_history_block(history_items)}\n\n"
        f"Evidence packet:\n{render_evidence_block(evidence_items)}\n\n"
        f"Question:\n{query_text}\n\n"
        "Write the final answer now. Include evidence IDs next to claims."
    )
    return [
        ChatCompletionMessage(role="system", content=system_prompt),
        ChatCompletionMessage(role="user", content=user_prompt),
    ]
