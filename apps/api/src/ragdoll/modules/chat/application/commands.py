from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.core.exceptions import ApplicationError
from ragdoll.core.logging import get_logger
from ragdoll.modules.documents.infrastructure.repository import DocumentsRepository
from ragdoll.modules.chat.api.schemas import ChatSendMessageResponse
from ragdoll.modules.chat.application.evidence import gather_chat_evidence
from ragdoll.modules.chat.application.service import (
    _truncate_title,
    build_chat_message_record,
    build_chat_suggestions,
    build_chat_session_detail,
    build_evidence_records,
    build_synthesis_messages,
    citations_for_synthesized_answer,
    compose_deterministic_evidence_answer,
)
from ragdoll.modules.chat.infrastructure.repository import ChatRepository
from ragdoll.modules.search.api.schemas import SearchMode
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids, resolve_single_owned_space
from ragdoll.platform.db.models import ChatMessage, ChatSession
from ragdoll.platform.llm import get_chat_completion_service

logger = get_logger("ragdoll.modules.chat.commands")


def create_chat_session(
    session: Session,
    subject: str,
    *,
    space_scope: SpaceScope,
    document_id: UUID | None = None,
) -> ChatSession:
    owner_user_id = UUID(subject)
    space = resolve_single_owned_space(session, owner_user_id, space_scope)
    scoped_document_id: UUID | None = None
    if document_id is not None:
        document = DocumentsRepository(session).get_visible_or_404(owner_user_id, document_id)
        if document.space_id != space.id:
            raise ApplicationError(
                "document_id must belong to the selected Space.",
                status_code=422,
                title="Request validation failed",
                type_uri="https://ragdoll.dev/problems/request-validation",
                code="request_validation_failed",
            )
        scoped_document_id = document.id
    chat_session = ChatSession(
        space_id=space.id,
        owner_user_id=owner_user_id,
        document_id=scoped_document_id,
        title="New chat",
    )
    repo = ChatRepository(session)
    repo.add_session(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


def send_chat_message(
    session: Session,
    subject: str,
    chat_session: ChatSession,
    *,
    content: str,
) -> ChatSendMessageResponse:
    query_text = content.strip()
    if not query_text:
        raise ApplicationError(
            "content must not be blank.",
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        )

    repo = ChatRepository(session)
    prior_messages = list(chat_session.messages)
    user_message = ChatMessage(
        session_id=chat_session.id,
        space_id=chat_session.space_id,
        author_user_id=UUID(subject),
        role="user",
        content=query_text,
    )
    repo.add_message(user_message)

    evidence_bundle = gather_chat_evidence(
        session,
        subject,
        chat_session,
        query_text=query_text,
        prior_messages=prior_messages,
    )
    synthesis_messages = build_synthesis_messages(
        query_text=query_text,
        evidence_items=evidence_bundle.evidence_items,
        history_items=evidence_bundle.history_items,
    )
    degraded = False
    try:
        answer_text = get_chat_completion_service().generate(synthesis_messages).strip()
        if not answer_text:
            raise ValueError("Chat synthesis returned a blank answer.")
    except Exception as exc:
        logger.warning(
            "chat_synthesis_failed session_id=%s space_id=%s document_id=%s error_type=%s error=%s",
            chat_session.id,
            chat_session.space_id,
            chat_session.document_id,
            type(exc).__name__,
            exc,
        )
        answer_text = compose_deterministic_evidence_answer(
            query_text=query_text,
            evidence_items=evidence_bundle.evidence_items,
        )
        degraded = True

    citations = citations_for_synthesized_answer(answer_text, evidence_bundle.evidence_items)
    suggestions = build_chat_suggestions(evidence_bundle.retrieval_results)
    evidence_records = build_evidence_records(evidence_bundle.evidence_items)
    assistant_message = ChatMessage(
        session_id=chat_session.id,
        space_id=chat_session.space_id,
        author_user_id=None,
        role="assistant",
        content=answer_text,
        citations=[citation.model_dump(mode="json") for citation in citations],
        suggestions=[suggestion.model_dump(mode="json") for suggestion in suggestions],
        evidence=[record.model_dump(mode="json") for record in evidence_records],
        retrieval_mode=SearchMode.COMBINED.value,
        degraded=degraded,
    )
    repo.add_message(assistant_message)
    if len(chat_session.messages) == 0 and chat_session.title == "New chat":
        chat_session.title = _truncate_title(query_text)
    session.commit()
    session.refresh(chat_session)
    session.refresh(user_message)
    session.refresh(assistant_message)
    refreshed = repo.get_visible_or_404([chat_session.space_id], chat_session.id)
    return ChatSendMessageResponse(
        session=build_chat_session_detail(refreshed),
        user_message=build_chat_message_record(user_message),
        assistant_message=build_chat_message_record(assistant_message),
    )
