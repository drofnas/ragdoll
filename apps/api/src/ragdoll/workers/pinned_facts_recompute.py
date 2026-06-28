from __future__ import annotations

from uuid import UUID

from ragdoll.modules.pinned_facts.application.service import recheck_space_facts
from ragdoll.platform.db.session import get_session_factory


def recompute_space(subject: str, *, space_id: UUID) -> None:
    session = get_session_factory()()
    try:
        recheck_space_facts(session, subject, space_id=space_id)
    finally:
        session.close()
