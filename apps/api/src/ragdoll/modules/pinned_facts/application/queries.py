from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.api.shared_schemas import SpaceScope
from ragdoll.core.pagination import PaginationParams
from ragdoll.modules.pinned_facts.api.schemas import (
    PinnedFactCandidateListResponse,
    PinnedFactDetail,
    PinnedFactHistoryResponse,
    PinnedFactListResponse,
    PinnedFactSortKey,
    PinnedFactSummary,
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
    name: str | None,
    status: str | None,
    created_by: str | None,
    updated_by: str | None,
    created_date: date | None,
    updated_date: date | None,
    sort_key: PinnedFactSortKey,
    descending: bool,
) -> PinnedFactListResponse:
    repo = PinnedFactsRepository(session)
    facts = repo.list_facts(resolve_owned_space_ids(session, UUID(subject), space_scope))
    summaries = [build_fact_summary(session, fact) for fact in facts]
    filtered = [
        summary
        for summary in summaries
        if _matches_summary(
            summary,
            name=name,
            status=status,
            created_by=created_by,
            updated_by=updated_by,
            created_date=created_date,
            updated_date=updated_date,
        )
    ]
    filtered.sort(key=lambda item: _summary_sort_value(item, sort_key), reverse=descending)
    total = len(filtered)
    page_facts = filtered[pagination.offset : pagination.offset + pagination.page_size]
    return PinnedFactListResponse(
        items=page_facts,
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def _actor_label(actor: PinnedFactSummary["created_by"] | PinnedFactSummary["updated_by"]) -> str:
    return (actor.full_name or actor.email or "").strip()


def _contains(value: str, query: str | None) -> bool:
    if query is None or not query.strip():
        return True
    return query.strip().lower() in value.lower()


def _matches_summary(
    summary: PinnedFactSummary,
    *,
    name: str | None,
    status: str | None,
    created_by: str | None,
    updated_by: str | None,
    created_date: date | None,
    updated_date: date | None,
) -> bool:
    return (
        _contains(summary.title, name)
        and _contains(summary.status, status)
        and _contains(_actor_label(summary.created_by), created_by)
        and _contains(_actor_label(summary.updated_by), updated_by)
        and (created_date is None or summary.created_at.date() == created_date)
        and (updated_date is None or summary.updated_at.date() == updated_date)
    )


def _summary_sort_value(summary: PinnedFactSummary, sort_key: PinnedFactSortKey) -> tuple[object, str]:
    if sort_key == "status":
        return (summary.status.lower(), summary.title.lower())
    if sort_key == "created_by":
        return (_actor_label(summary.created_by).lower(), summary.title.lower())
    if sort_key == "updated_by":
        return (_actor_label(summary.updated_by).lower(), summary.title.lower())
    if sort_key == "created_at":
        return (summary.created_at, summary.title.lower())
    if sort_key == "updated_at":
        return (summary.updated_at, summary.title.lower())
    return (summary.title.lower(), summary.key.lower())


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
