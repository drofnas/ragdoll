from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from ragdoll.core.exceptions import ApplicationError
from ragdoll.platform.db.models import PinnedFact, PinnedFactCandidate, PinnedFactHistory


class PinnedFactsRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_fact(self, fact: PinnedFact) -> None:
        self.session.add(fact)

    def list_facts(self, space_ids: list[UUID]) -> list[PinnedFact]:
        stmt = (
            select(PinnedFact)
            .where(PinnedFact.space_id.in_(space_ids))
            .order_by(PinnedFact.created_at.asc(), PinnedFact.key.asc())
        )
        return list(self.session.scalars(stmt))

    def list_active_facts(self, space_ids: list[UUID]) -> list[PinnedFact]:
        stmt = (
            select(PinnedFact)
            .where(PinnedFact.space_id.in_(space_ids), PinnedFact.is_active.is_(True))
            .order_by(PinnedFact.created_at.asc(), PinnedFact.key.asc())
        )
        return list(self.session.scalars(stmt))

    def list_active_facts_for_space(self, space_id: UUID) -> list[PinnedFact]:
        stmt = (
            select(PinnedFact)
            .where(PinnedFact.space_id == space_id, PinnedFact.is_active.is_(True))
            .order_by(PinnedFact.created_at.asc(), PinnedFact.key.asc())
        )
        return list(self.session.scalars(stmt))

    def get_visible_or_404(self, space_ids: list[UUID], fact_id: UUID) -> PinnedFact:
        stmt = select(PinnedFact).where(PinnedFact.id == fact_id, PinnedFact.space_id.in_(space_ids))
        fact = self.session.scalar(stmt)
        if fact is None:
            raise ApplicationError(
                "Requested pinned fact was not found.",
                status_code=404,
                title="Not found",
                type_uri="https://ragdoll.dev/problems/not-found",
                code="pinned_fact_not_found",
            )
        return fact

    def add_candidate(self, candidate: PinnedFactCandidate) -> None:
        self.session.add(candidate)

    def get_candidate_by_idempotency(self, fact_id: UUID, idempotency_key: str) -> PinnedFactCandidate | None:
        stmt = select(PinnedFactCandidate).where(
            PinnedFactCandidate.pinned_fact_id == fact_id,
            PinnedFactCandidate.idempotency_key == idempotency_key,
        )
        return self.session.scalar(stmt)

    def list_candidates_for_fact(self, fact_id: UUID) -> list[PinnedFactCandidate]:
        stmt = (
            select(PinnedFactCandidate)
            .where(PinnedFactCandidate.pinned_fact_id == fact_id)
            .order_by(PinnedFactCandidate.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def get_candidate_visible_or_404(self, space_ids: list[UUID], candidate_id: UUID) -> PinnedFactCandidate:
        stmt = (
            select(PinnedFactCandidate)
            .join(PinnedFact, PinnedFact.id == PinnedFactCandidate.pinned_fact_id)
            .where(PinnedFactCandidate.id == candidate_id, PinnedFact.space_id.in_(space_ids))
        )
        candidate = self.session.scalar(stmt)
        if candidate is None:
            raise ApplicationError(
                "Requested pinned fact candidate was not found.",
                status_code=404,
                title="Not found",
                type_uri="https://ragdoll.dev/problems/not-found",
                code="pinned_fact_candidate_not_found",
            )
        return candidate

    def add_history(self, history: PinnedFactHistory) -> None:
        self.session.add(history)

    def list_history_for_fact(self, fact_id: UUID) -> list[PinnedFactHistory]:
        stmt = (
            select(PinnedFactHistory)
            .where(PinnedFactHistory.pinned_fact_id == fact_id)
            .order_by(PinnedFactHistory.created_at.desc())
        )
        return list(self.session.scalars(stmt))

    def get_history_visible_or_404(self, space_ids: list[UUID], history_id: UUID) -> PinnedFactHistory:
        stmt = (
            select(PinnedFactHistory)
            .join(PinnedFact, PinnedFact.id == PinnedFactHistory.pinned_fact_id)
            .where(PinnedFactHistory.id == history_id, PinnedFact.space_id.in_(space_ids))
        )
        history = self.session.scalar(stmt)
        if history is None:
            raise ApplicationError(
                "Requested pinned fact history entry was not found.",
                status_code=404,
                title="Not found",
                type_uri="https://ragdoll.dev/problems/not-found",
                code="pinned_fact_history_not_found",
            )
        return history
