from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.modules.spaces.api.schemas import SpaceListResponse, SpaceResponse
from ragdoll.modules.spaces.infrastructure.repository import SpacesRepository
from ragdoll.platform.db.models import Space


def build_space_response(
    space: Space,
    *,
    document_count: int = 0,
    pinned_fact_count: int = 0,
) -> SpaceResponse:
    return SpaceResponse(
        id=space.id,
        owner_user_id=space.owner_user_id,
        name=space.name,
        description=space.description,
        is_default=space.is_default,
        document_count=document_count,
        pinned_fact_count=pinned_fact_count,
        archived_at=space.archived_at,
        created_at=space.created_at,
        updated_at=space.updated_at,
    )


def build_space_response_with_counts(session: Session, space: Space) -> SpaceResponse:
    document_count, pinned_fact_count = SpacesRepository(session).counts_for_space(space.id)
    return build_space_response(
        space,
        document_count=document_count,
        pinned_fact_count=pinned_fact_count,
    )


def list_spaces(session: Session, owner_user_id: UUID, *, include_archived: bool) -> SpaceListResponse:
    repo = SpacesRepository(session)
    spaces = repo.list_by_owner_with_counts(owner_user_id, include_archived=include_archived)
    return SpaceListResponse(
        items=[
            build_space_response(
                space,
                document_count=document_count,
                pinned_fact_count=pinned_fact_count,
            )
            for space, document_count, pinned_fact_count in spaces
        ]
    )


def get_owned_space_or_404(session: Session, owner_user_id: UUID, space_id: UUID) -> Space:
    repo = SpacesRepository(session)
    return repo.get_owned_or_404(owner_user_id, space_id)
