from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.core.pagination import PaginationParams
from ragdoll.modules.chat.api.schemas import ChatSessionDetail, ChatSessionListResponse
from ragdoll.modules.chat.application.service import build_chat_session_detail, build_chat_session_summary
from ragdoll.modules.chat.infrastructure.repository import ChatRepository
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids


def list_chat_sessions(
    session: Session,
    subject: str,
    pagination: PaginationParams,
    *,
    space_scope: SpaceScope,
) -> ChatSessionListResponse:
    repo = ChatRepository(session)
    sessions = repo.list_sessions(resolve_owned_space_ids(session, UUID(subject), space_scope))
    total = len(sessions)
    page_items = sessions[pagination.offset : pagination.offset + pagination.page_size]
    return ChatSessionListResponse(
        items=[build_chat_session_summary(item) for item in page_items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_chat_session_detail(session: Session, subject: str, session_id: UUID) -> ChatSessionDetail:
    repo = ChatRepository(session)
    chat_session = repo.get_visible_or_404(
        resolve_owned_space_ids(session, UUID(subject), SpaceScope(all_spaces=True)),
        session_id,
    )
    return build_chat_session_detail(chat_session)
