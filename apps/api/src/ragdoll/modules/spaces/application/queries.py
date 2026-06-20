from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.modules.spaces.api.schemas import SpaceListResponse, SpaceResponse
from ragdoll.modules.spaces.infrastructure.repository import SpacesRepository
from ragdoll.platform.db.models import Space


def build_space_response(space: Space) -> SpaceResponse:
    return SpaceResponse.model_validate(space)


def list_spaces(session: Session, owner_user_id: UUID, *, include_archived: bool) -> SpaceListResponse:
    repo = SpacesRepository(session)
    spaces = repo.list_by_owner(owner_user_id, include_archived=include_archived)
    return SpaceListResponse(items=[build_space_response(space) for space in spaces])


def get_owned_space_or_404(session: Session, owner_user_id: UUID, space_id: UUID) -> Space:
    repo = SpacesRepository(session)
    return repo.get_owned_or_404(owner_user_id, space_id)
