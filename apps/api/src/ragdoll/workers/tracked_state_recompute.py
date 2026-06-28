from __future__ import annotations

from uuid import UUID

from ragdoll.modules.tracked_state.application.service import recompute_space_fields
from ragdoll.platform.db.session import get_session_factory


def recompute_space(subject: str, *, space_id: UUID) -> None:
    session = get_session_factory()()
    try:
        recompute_space_fields(session, subject, space_id=space_id)
    finally:
        session.close()
