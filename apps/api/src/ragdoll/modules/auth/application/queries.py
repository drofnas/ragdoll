from __future__ import annotations

from sqlalchemy.orm import Session

from ragdoll.core.auth import AuthenticatedPrincipal
from ragdoll.modules.users.application.queries import build_user_profile_response, get_user_by_subject


def get_current_user_profile(session: Session, current_user: AuthenticatedPrincipal):
    user = get_user_by_subject(session, current_user.subject)
    return build_user_profile_response(user)
