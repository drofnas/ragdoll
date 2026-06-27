from __future__ import annotations

from urllib.parse import parse_qs
from sqlalchemy import delete, select

from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError, AuthenticationRequiredError
from ragdoll.core.security import create_access_token, get_password_hash, verify_password
from ragdoll.modules.auth.api.schemas import LoginTokenResponse, RegisterRequest
from ragdoll.modules.spaces.application.commands import create_default_space_for_user
from ragdoll.modules.spaces.infrastructure.repository import SpacesRepository
from ragdoll.modules.users.application.queries import build_user_profile_response
from ragdoll.modules.users.infrastructure.repository import UsersRepository
from ragdoll.platform.db.models import (
    CanonicalEntity,
    ChangeEvent,
    ChangeEventRead,
    ChatMessage,
    ChatSession,
    CorrectionRecord,
    Document,
    DocumentChunk,
    DocumentChunkVector,
    DocumentProcessingJob,
    Entity,
    GraphEdge,
    GraphNode,
    Space,
    TrackedField,
    TrackedFieldValue,
    UsageEvent,
    User,
    UserUsageSnapshot,
)
from ragdoll.platform.graph import GraphCleanupService
from ragdoll.platform.storage import DocumentStorageService
from ragdoll.platform.vector import VectorCleanupService


def register_user(session: Session, payload: RegisterRequest) -> User:
    """Register a new user and create the default Space in one transaction."""
    users_repo = UsersRepository(session)
    if users_repo.get_by_email(payload.email) is not None:
        raise ApplicationError(
            "Email already registered.",
            status_code=409,
            title="Conflict",
            type_uri="https://ragdoll.dev/problems/conflict",
            code="email_already_registered",
        )

    user = User(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
    )
    users_repo.add(user)
    session.flush()
    create_default_space_for_user(session, user.id)
    session.commit()
    session.refresh(user)
    return user


def login_user(session: Session, username: str, password: str) -> LoginTokenResponse:
    """Authenticate a user and return the bearer token payload."""
    users_repo = UsersRepository(session)
    user = users_repo.get_by_email(username)
    if user is None or not verify_password(password, user.hashed_password):
        raise AuthenticationRequiredError("Incorrect username or password.")

    users_repo.record_login(user)
    session.commit()
    return LoginTokenResponse(
        access_token=create_access_token({"sub": str(user.id), "email": user.email}),
        token_type="bearer",
        must_change_password=user.must_change_password,
    )


def reset_user_workspace(
    session: Session,
    user: User,
    *,
    storage: DocumentStorageService,
    vector_cleanup: VectorCleanupService,
    graph_cleanup: GraphCleanupService,
) -> None:
    spaces = SpacesRepository(session).list_by_owner(user.id, include_archived=True)
    space_ids = [space.id for space in spaces]

    documents = list(
        session.scalars(select(Document).where(Document.space_id.in_(space_ids)))
    ) if space_ids else []
    for document in documents:
        storage.delete_original_file(document.storage_key)
        storage.delete_derived_artifacts(document.id)
        vector_cleanup.cleanup_document(document.id)
        graph_cleanup.cleanup_document(document.id)

    session.execute(delete(UsageEvent).where(UsageEvent.user_id == user.id))
    session.execute(delete(UserUsageSnapshot).where(UserUsageSnapshot.user_id == user.id))

    if space_ids:
        session.execute(
            delete(ChangeEventRead).where(
                ChangeEventRead.change_event_id.in_(select(ChangeEvent.id).where(ChangeEvent.space_id.in_(space_ids)))
            )
        )
        session.execute(delete(ChangeEventRead).where(ChangeEventRead.user_id == user.id))
        session.execute(delete(TrackedFieldValue).where(TrackedFieldValue.space_id.in_(space_ids)))
        session.execute(delete(ChatMessage).where(ChatMessage.space_id.in_(space_ids)))
        session.execute(delete(GraphEdge).where(GraphEdge.space_id.in_(space_ids)))
        session.execute(delete(DocumentChunkVector).where(DocumentChunkVector.space_id.in_(space_ids)))
        session.execute(delete(Entity).where(Entity.space_id.in_(space_ids)))
        session.execute(delete(DocumentProcessingJob).where(DocumentProcessingJob.space_id.in_(space_ids)))
        session.execute(delete(ChangeEvent).where(ChangeEvent.space_id.in_(space_ids)))
        session.execute(delete(CorrectionRecord).where(CorrectionRecord.space_id.in_(space_ids)))
        session.execute(delete(TrackedField).where(TrackedField.space_id.in_(space_ids)))
        session.execute(delete(ChatSession).where(ChatSession.space_id.in_(space_ids)))
        session.execute(delete(GraphNode).where(GraphNode.space_id.in_(space_ids)))
        session.execute(delete(CanonicalEntity).where(CanonicalEntity.space_id.in_(space_ids)))
        session.execute(delete(DocumentChunk).where(DocumentChunk.space_id.in_(space_ids)))
        session.execute(delete(Document).where(Document.space_id.in_(space_ids)))
        session.execute(delete(Space).where(Space.id.in_(space_ids)))

    session.flush()
    create_default_space_for_user(session, user.id)
    session.commit()


def parse_oauth_password_form(raw_body: bytes) -> tuple[str, str]:
    """Parse the legacy OAuth2 password form without python-multipart."""
    values = parse_qs(raw_body.decode("utf-8"), keep_blank_values=False)
    username = (values.get("username") or [""])[0].strip().lower()
    password = (values.get("password") or [""])[0]
    if not username or not password:
        raise ApplicationError(
            "The request payload or parameters did not match the expected schema.",
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        )
    return username, password


def build_registration_response(user: User):
    return build_user_profile_response(user)
