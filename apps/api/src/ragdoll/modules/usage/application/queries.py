from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.core.instance_policy import resolve_instance_limits
from ragdoll.modules.users.application.queries import get_user_by_subject
from ragdoll.modules.usage.api.schemas import (
    UsageAmounts,
    UsageLimitSet,
    UsagePercentages,
    UsageResetTimers,
    UsageStatusFlags,
    UsageSummaryResponse,
)
from ragdoll.modules.usage.domain.policies import percentage_used
from ragdoll.modules.usage.infrastructure.repository import UsageRepository

EVENT_CHAT_TOKENS = "chat_tokens"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def recompute_usage_snapshot(session: Session, user_id: UUID):
    repo = UsageRepository(session)
    snapshot = repo.get_or_create_snapshot(user_id)
    document_count, chunk_count, storage_bytes, _ = repo.owned_document_metrics(user_id)
    now = utc_now()
    since_5h = now - timedelta(hours=5)
    since_week = now - timedelta(days=7)

    snapshot.document_count = document_count
    snapshot.chunk_count = chunk_count
    snapshot.storage_bytes = storage_bytes
    snapshot.tokens_5h = repo.usage_total_since(user_id, EVENT_CHAT_TOKENS, since_5h)
    snapshot.tokens_week = repo.usage_total_since(user_id, EVENT_CHAT_TOKENS, since_week)
    snapshot.updated_at = now
    session.commit()
    session.refresh(snapshot)
    return snapshot


def get_usage_summary(session: Session, subject: str) -> UsageSummaryResponse:
    user = get_user_by_subject(session, subject)
    repo = UsageRepository(session)
    snapshot = recompute_usage_snapshot(session, user.id)
    document_count, chunk_count, storage_bytes, partially_indexed_documents = repo.owned_document_metrics(user.id)
    now = utc_now()
    since_5h = now - timedelta(hours=5)
    since_week = now - timedelta(days=7)
    reset_5h = repo.earliest_usage_since(user.id, EVENT_CHAT_TOKENS, since_5h)
    reset_week = repo.earliest_usage_since(user.id, EVENT_CHAT_TOKENS, since_week)
    limits = resolve_instance_limits()

    usage = UsageAmounts(
        documents=document_count,
        chunks=chunk_count,
        storage_bytes=storage_bytes,
        tokens_5h=int(snapshot.tokens_5h or 0),
        tokens_week=int(snapshot.tokens_week or 0),
    )
    return UsageSummaryResponse(
        usage=usage,
        limits=UsageLimitSet(
            documents=limits.documents,
            max_file_size_bytes=limits.max_file_size_bytes,
            chunks=limits.chunks,
            storage_bytes=limits.storage_bytes,
            tokens_5h=limits.tokens_5h,
            tokens_week=limits.tokens_week,
            retrieval_chunks=limits.retrieval_chunks,
            output_tokens=limits.output_tokens,
            per_document_chunks=limits.per_document_chunks,
        ),
        percent_used=UsagePercentages(
            documents=percentage_used(usage.documents, limits.documents),
            chunks=percentage_used(usage.chunks, limits.chunks),
            storage_bytes=percentage_used(usage.storage_bytes, limits.storage_bytes),
            tokens_5h=percentage_used(usage.tokens_5h, limits.tokens_5h),
            tokens_week=percentage_used(usage.tokens_week, limits.tokens_week),
        ),
        resets_at=UsageResetTimers(
            tokens_5h_resets_at=reset_5h + timedelta(hours=5) if reset_5h else None,
            tokens_week_resets_at=reset_week + timedelta(days=7) if reset_week else None,
        ),
        status=UsageStatusFlags(
            chat_blocked=bool(limits.tokens_5h is not None and usage.tokens_5h >= limits.tokens_5h)
            or bool(limits.tokens_week is not None and usage.tokens_week >= limits.tokens_week),
            upload_blocked=bool(limits.documents is not None and usage.documents >= limits.documents)
            or bool(limits.storage_bytes is not None and usage.storage_bytes >= limits.storage_bytes),
            partially_indexed_documents=partially_indexed_documents,
        ),
    )
