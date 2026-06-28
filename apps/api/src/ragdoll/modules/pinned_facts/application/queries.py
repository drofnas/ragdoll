from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.core.pagination import PaginationParams
from ragdoll.modules.pinned_facts.api.schemas import (
    PinnedFactCandidateListResponse,
    PinnedFactDetail,
    PinnedFactHistoryResponse,
    PinnedFactListResponse,
)
from ragdoll.modules.pinned_facts.application.service import (
    build_candidate,
    build_fact_detail,
    build_fact_summary,
    build_history_entry,
)
from ragdoll.modules.pinned_facts.infrastructure.repository import PinnedFactsRepository
from ragdoll.modules.spaces.application.scope import resolve_owned_space_ids


def list_pinned_facts(
    session: Session,
    subject: str,
    pagination: PaginationParams,
    *,
    space_scope: SpaceScope,
) -> PinnedFactListResponse:
    repo = PinnedFactsRepository(session)
    facts = repo.list_facts(resolve_owned_space_ids(session, UUID(subject), space_scope))
    total = len(facts)
    page_facts = facts[pagination.offset : pagination.offset + pagination.page_size]
    return PinnedFactListResponse(
        items=[build_fact_summary(session, fact) for fact in page_facts],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_pinned_fact_detail(session: Session, subject: str, fact_id: UUID, *, space_scope: SpaceScope) -> PinnedFactDetail:
    fact = PinnedFactsRepository(session).get_visible_or_404(resolve_owned_space_ids(session, UUID(subject), space_scope), fact_id)
    return build_fact_detail(session, fact)


def list_pinned_fact_candidates(
    session: Session,
    subject: str,
    fact_id: UUID,
    *,
    space_scope: SpaceScope,
) -> PinnedFactCandidateListResponse:
    repo = PinnedFactsRepository(session)
    fact = repo.get_visible_or_404(resolve_owned_space_ids(session, UUID(subject), space_scope), fact_id)
    return PinnedFactCandidateListResponse(items=[build_candidate(item) for item in repo.list_candidates_for_fact(fact.id)])


def list_pinned_fact_history(
    session: Session,
    subject: str,
    fact_id: UUID,
    *,
    space_scope: SpaceScope,
) -> PinnedFactHistoryResponse:
    repo = PinnedFactsRepository(session)
    fact = repo.get_visible_or_404(resolve_owned_space_ids(session, UUID(subject), space_scope), fact_id)
    return PinnedFactHistoryResponse(items=[build_history_entry(item) for item in repo.list_history_for_fact(fact.id)])
