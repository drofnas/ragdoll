from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.core.exceptions import ApplicationError
from ragdoll.platform.db.models import Space
from ragdoll.modules.spaces.infrastructure.repository import SpacesRepository


def resolve_owned_space_ids(session: Session, owner_user_id: UUID, space_scope: SpaceScope) -> list[UUID]:
    """Resolve retrieval-read scope to explicit owned Space ids."""
    repo = SpacesRepository(session)

    if space_scope.space_id is not None:
        repo.get_owned_or_404(owner_user_id, space_scope.space_id)
        return [space_scope.space_id]

    if space_scope.all_spaces:
        return repo.list_active_owned_space_ids(owner_user_id)

    return [repo.get_default_owned_space_or_404(owner_user_id).id]


def resolve_single_owned_space(
    session: Session,
    owner_user_id: UUID,
    space_scope: SpaceScope,
    *,
    allow_all_spaces: bool = False,
) -> Space:
    """Resolve one owned Space for single-scope workflows."""
    repo = SpacesRepository(session)

    if space_scope.space_id is not None:
        return repo.get_owned_or_404(owner_user_id, space_scope.space_id)

    if space_scope.all_spaces:
        if allow_all_spaces:
            return repo.get_default_owned_space_or_404(owner_user_id)
        raise ApplicationError(
            "This workflow requires one concrete Space and does not support all_spaces=true.",
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        )

    return repo.get_default_owned_space_or_404(owner_user_id)
