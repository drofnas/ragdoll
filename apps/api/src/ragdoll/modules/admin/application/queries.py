from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.core.config import Settings
from ragdoll.core.exceptions import ApplicationError
from ragdoll.core.instance_policy import resolve_instance_limits
from ragdoll.core.pagination import PaginationParams
from ragdoll.modules.admin.api.schemas import (
    AdminEffectiveLimitsResponse,
    AdminManagedUserListResponse,
    AdminManagedUserResponse,
    UploadRateLimitPolicy,
)
from ragdoll.modules.users.infrastructure.repository import UsersRepository
from ragdoll.platform.db.models import User


def build_admin_user_response(user: User) -> AdminManagedUserResponse:
    return AdminManagedUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        must_change_password=user.must_change_password,
        last_login=user.last_login,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def list_managed_users(session: Session, pagination: PaginationParams) -> AdminManagedUserListResponse:
    repo = UsersRepository(session)
    items, total = repo.list_paginated(limit=pagination.page_size, offset=pagination.offset)
    return AdminManagedUserListResponse(
        items=[build_admin_user_response(user) for user in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


def get_managed_user(session: Session, user_id: UUID) -> AdminManagedUserResponse:
    user = UsersRepository(session).get_by_id(user_id)
    if user is None:
        raise ApplicationError(
            "The requested user was not found.",
            status_code=404,
            title="Not found",
            type_uri="https://ragdoll.dev/problems/not-found",
            code="user_not_found",
        )
    return build_admin_user_response(user)


def get_effective_limits(settings: Settings) -> AdminEffectiveLimitsResponse:
    limits = resolve_instance_limits(settings)
    return AdminEffectiveLimitsResponse(
        documents=limits.documents,
        max_file_size_bytes=limits.max_file_size_bytes,
        chunks=limits.chunks,
        storage_bytes=limits.storage_bytes,
        tokens_5h=limits.tokens_5h,
        tokens_week=limits.tokens_week,
        retrieval_chunks=limits.retrieval_chunks,
        output_tokens=limits.output_tokens,
        per_document_chunks=limits.per_document_chunks,
        upload_rate_limit=UploadRateLimitPolicy(
            enabled=settings.upload_rate_limit_enabled,
            requests=settings.upload_rate_limit_requests,
            window_seconds=settings.upload_rate_limit_window_seconds,
        ),
    )
