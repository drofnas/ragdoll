from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.core.pagination import PaginationParams
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids
from ragdoll.modules.tracked_state.api.schemas import (
    TrackedFieldDefinitionListResponse,
    TrackedStateConflictResponse,
    TrackedStateSummaryResponse,
)
from ragdoll.modules.tracked_state.application.service import build_field_conflict, build_field_definition, build_field_summary
from ragdoll.modules.tracked_state.infrastructure.repository import TrackedStateRepository


def list_tracked_fields(
    session: Session,
    subject: str,
    pagination: PaginationParams,
    *,
    space_scope: SpaceScope,
) -> TrackedFieldDefinitionListResponse:
    repo = TrackedStateRepository(session)
    fields = repo.list_fields(resolve_owned_space_ids(session, UUID(subject), space_scope))
    total = len(fields)
    page_fields = fields[pagination.offset : pagination.offset + pagination.page_size]
    return TrackedFieldDefinitionListResponse(
        items=[build_field_definition(field) for field in page_fields],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_tracked_summary(session: Session, subject: str, *, space_scope: SpaceScope) -> TrackedStateSummaryResponse:
    repo = TrackedStateRepository(session)
    fields = repo.list_active_fields(resolve_owned_space_ids(session, UUID(subject), space_scope))
    return TrackedStateSummaryResponse(items=[build_field_summary(session, subject, field) for field in fields])


def get_tracked_conflicts(session: Session, subject: str, *, space_scope: SpaceScope) -> TrackedStateConflictResponse:
    repo = TrackedStateRepository(session)
    fields = repo.list_active_fields(resolve_owned_space_ids(session, UUID(subject), space_scope))
    conflicts = [build_field_conflict(session, subject, field) for field in fields]
    return TrackedStateConflictResponse(items=[item for item in conflicts if item.status == "conflict"])
