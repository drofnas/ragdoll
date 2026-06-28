from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ragdoll.core.exceptions import ApplicationError
from ragdoll.platform.db.models import ChatMessage, ChatSession


class ChatRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_session(self, chat_session: ChatSession) -> None:
        self.session.add(chat_session)

    def add_message(self, message: ChatMessage) -> None:
        self.session.add(message)

    def list_sessions(self, space_ids: list[UUID]) -> list[ChatSession]:
        stmt = (
            select(ChatSession)
            .where(ChatSession.space_id.in_(space_ids))
            .options(selectinload(ChatSession.messages))
            .order_by(ChatSession.updated_at.desc(), ChatSession.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def get_visible_or_404(self, space_ids: list[UUID], session_id: UUID) -> ChatSession:
        stmt = (
            select(ChatSession)
            .where(ChatSession.id == session_id, ChatSession.space_id.in_(space_ids))
            .options(selectinload(ChatSession.messages))
        )
        chat_session = self.session.scalar(stmt)
        if chat_session is None:
            raise ApplicationError(
                "Requested chat session was not found.",
                status_code=404,
                title="Not found",
                type_uri="https://ragdoll.dev/problems/not-found",
                code="chat_session_not_found",
            )
        return chat_session
