from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError
from ragdoll.modules.spaces.api.schemas import SpaceCreateRequest, SpaceUpdateRequest
from ragdoll.modules.spaces.domain.policies import DEFAULT_SPACE_NAME, ensure_space_can_be_archived
from ragdoll.modules.spaces.infrastructure.repository import SpacesRepository
from ragdoll.platform.db.models import Space


def create_default_space_for_user(session: Session, owner_user_id: UUID) -> Space:
    repo = SpacesRepository(session)
    space = Space(
        owner_user_id=owner_user_id,
        name=DEFAULT_SPACE_NAME,
        description=None,
        is_default=True,
    )
    repo.add(space)
    return space


def create_space(session: Session, owner_user_id: UUID, payload: SpaceCreateRequest) -> Space:
    repo = SpacesRepository(session)
    space = Space(
        owner_user_id=owner_user_id,
        name=payload.name,
        description=payload.description,
        is_default=False,
    )
    repo.add(space)
    session.commit()
    session.refresh(space)
    return space


def update_space(
    session: Session,
    owner_user_id: UUID,
    space: Space,
    payload: SpaceUpdateRequest,
) -> Space:
    repo = SpacesRepository(session)

    if payload.archived and payload.is_default is True:
        raise ApplicationError(
            "A space cannot be both archived and default.",
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        )

    if payload.name is not None:
        space.name = payload.name
    if payload.description is not None:
        space.description = payload.description

    if payload.is_default is True:
        if space.archived_at is not None and payload.archived is not False:
            raise ApplicationError(
                "Archived spaces cannot become the default space.",
                status_code=422,
                title="Request validation failed",
                type_uri="https://ragdoll.dev/problems/request-validation",
                code="request_validation_failed",
            )
        repo.clear_default_for_owner(owner_user_id, exclude_space_id=space.id)
        space.is_default = True
    elif payload.is_default is False and space.is_default:
        raise ApplicationError(
            "The default space must be reassigned before it can be unset.",
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        )

    if payload.archived is not None:
        if payload.archived:
            ensure_space_can_be_archived(space)
            repo.archive(space)
        else:
            repo.unarchive(space)

    session.commit()
    session.refresh(space)
    return space


def archive_space(session: Session, space: Space) -> Space:
    ensure_space_can_be_archived(space)
    repo = SpacesRepository(session)
    repo.archive(space)
    session.commit()
    session.refresh(space)
    return space
