from ragdoll.api.dependencies import CurrentUserDep, DatabaseSessionDep
from ragdoll.api.shared_schemas import ProblemResponse
from ragdoll.modules.usage.api.schemas import UsageSummaryResponse
from ragdoll.modules.usage.application.queries import get_usage_summary

from fastapi import APIRouter

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get(
    "/me",
    response_model=UsageSummaryResponse,
    responses={
        401: {"model": ProblemResponse, "description": "Authentication required."},
    },
)
def read_my_usage(current_user: CurrentUserDep, db: DatabaseSessionDep) -> UsageSummaryResponse:
    return get_usage_summary(db, current_user.subject)
