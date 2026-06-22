from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from ragdoll.api.dependencies import CurrentUserDep, DatabaseSessionDep, PaginationDep, SpaceScopeDep
from ragdoll.api.shared_schemas import ProblemResponse, SpaceScope
from ragdoll.modules.chat.api.schemas import (
    ChatSendMessageRequest,
    ChatSendMessageResponse,
    ChatSessionDetail,
    ChatSessionListResponse,
    ChatSessionSummary,
)
from ragdoll.modules.chat.application.commands import create_chat_session, send_chat_message
from ragdoll.modules.chat.application.queries import get_chat_session_detail, list_chat_sessions
from ragdoll.modules.chat.application.service import build_chat_session_summary
from ragdoll.modules.chat.infrastructure.repository import ChatRepository
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids

router = APIRouter(prefix="/chat", tags=["chat"])

COMMON_RESPONSES = {
    401: {"model": ProblemResponse, "description": "Authentication required."},
    404: {"model": ProblemResponse, "description": "Requested chat session was not found."},
    422: {"model": ProblemResponse, "description": "Request validation failed."},
}


@router.get("/sessions", response_model=ChatSessionListResponse, responses=COMMON_RESPONSES)
def read_chat_sessions(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    pagination: PaginationDep,
    space_scope: SpaceScopeDep,
) -> ChatSessionListResponse:
    return list_chat_sessions(db, current_user.subject, pagination, space_scope=space_scope)


@router.post("/sessions", response_model=ChatSessionSummary, responses=COMMON_RESPONSES)
def post_chat_session(
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
    space_scope: SpaceScopeDep,
) -> ChatSessionSummary:
    chat_session = create_chat_session(db, current_user.subject, space_scope=space_scope)
    return build_chat_session_summary(chat_session)


@router.get("/sessions/{session_id}", response_model=ChatSessionDetail, responses=COMMON_RESPONSES)
def read_chat_session_detail(
    session_id: UUID,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
) -> ChatSessionDetail:
    return get_chat_session_detail(db, current_user.subject, session_id)


@router.post("/sessions/{session_id}/messages", response_model=ChatSendMessageResponse, responses=COMMON_RESPONSES)
def post_chat_message(
    session_id: UUID,
    payload: ChatSendMessageRequest,
    current_user: CurrentUserDep,
    db: DatabaseSessionDep,
) -> ChatSendMessageResponse:
    repo = ChatRepository(db)
    chat_session = repo.get_visible_or_404(
        resolve_owned_space_ids(db, UUID(current_user.subject), SpaceScope(all_spaces=True)),
        session_id,
    )
    return send_chat_message(db, current_user.subject, chat_session, content=payload.content)
