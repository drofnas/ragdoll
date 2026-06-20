from __future__ import annotations

from ragdoll.core.exceptions import ApplicationError
from ragdoll.platform.db.models import Space


DEFAULT_SPACE_NAME = "Default Space"


def ensure_space_can_be_archived(space: Space) -> None:
    if space.is_default:
        raise ApplicationError(
            "Default space cannot be archived.",
            status_code=403,
            title="Forbidden",
            type_uri="https://ragdoll.dev/problems/forbidden",
            code="default_space_cannot_be_archived",
        )
