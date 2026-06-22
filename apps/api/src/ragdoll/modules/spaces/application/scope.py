from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
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
