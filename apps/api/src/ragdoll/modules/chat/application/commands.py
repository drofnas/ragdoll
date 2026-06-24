from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.core.exceptions import ApplicationError
from ragdoll.modules.documents.infrastructure.repository import DocumentsRepository
from ragdoll.modules.chat.api.schemas import ChatSendMessageResponse
from ragdoll.modules.chat.application.service import (
    _truncate_title,
    build_chat_message_record,
    build_chat_session_detail,
    collect_verified_corrections,
    compose_fallback_answer,
)
from ragdoll.modules.chat.infrastructure.repository import ChatRepository
from ragdoll.modules.search.api.schemas import SearchMode
from ragdoll.modules.search.application.evidence import retrieve_search_results
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids, resolve_single_owned_space
from ragdoll.platform.db.models import ChatMessage, ChatSession, Document


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
    user_message = ChatMessage(
        session_id=chat_session.id,
        space_id=chat_session.space_id,
        author_user_id=UUID(subject),
        role="user",
        content=query_text,
    )
    repo.add_message(user_message)

    retrieval_results = retrieve_search_results(
        session,
        subject,
        space_scope=SpaceScope(space_id=chat_session.space_id),
        query_text=query_text,
        mode=SearchMode.COMBINED,
        document_id=chat_session.document_id,
        limit=5,
    )
    document_context: dict[UUID, str] = {}
    for result in retrieval_results:
        if result.document is None:
            continue
        document_context.setdefault(result.document.id, _document_context_text(session.get(Document, result.document.id)))
    verified_corrections = collect_verified_corrections(session, space_id=chat_session.space_id, query_text=query_text)
    answer_text, citations, suggestions = compose_fallback_answer(
        query_text=query_text,
        retrieval_results=retrieval_results,
        verified_corrections=verified_corrections,
        document_id=chat_session.document_id,
        document_context=document_context,
    )
    assistant_message = ChatMessage(
        session_id=chat_session.id,
        space_id=chat_session.space_id,
        author_user_id=None,
        role="assistant",
        content=answer_text,
        citations=[citation.model_dump(mode="json") for citation in citations],
        suggestions=[suggestion.model_dump(mode="json") for suggestion in suggestions],
        retrieval_mode=SearchMode.COMBINED.value,
        degraded=True,
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


def _document_context_text(document: Document | None) -> str:
    if document is None:
        return ""
    if document.preview_text:
        return document.preview_text
    if document.original_text_content:
        return document.original_text_content[:500]
    return ""
