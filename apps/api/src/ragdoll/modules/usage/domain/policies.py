from __future__ import annotations

from dataclasses import dataclass

from ragdoll.core.feature_flags import PlanTier


@dataclass(frozen=True)
class PlanLimits:
    documents: int | None
    max_file_size_bytes: int | None
    chunks: int | None
    storage_bytes: int | None
    tokens_5h: int | None
    tokens_week: int | None
    retrieval_chunks: int
    output_tokens: int
    per_document_chunks: int


FREE_LIMITS = PlanLimits(
    documents=25,
    max_file_size_bytes=10 * 1024 * 1024,
    chunks=5000,
    storage_bytes=500 * 1024 * 1024,
    tokens_5h=50_000,
    tokens_week=200_000,
    retrieval_chunks=6,
    output_tokens=400,
    per_document_chunks=300,
)

PRO_LIMITS = PlanLimits(
    documents=250,
    max_file_size_bytes=50 * 1024 * 1024,
    chunks=50_000,
    storage_bytes=10 * 1024 * 1024 * 1024,
    tokens_5h=200_000,
    tokens_week=1_000_000,
    retrieval_chunks=12,
    output_tokens=1200,
    per_document_chunks=300,
)

INTERNAL_LIMITS = PlanLimits(
    documents=None,
    max_file_size_bytes=None,
    chunks=None,
    storage_bytes=None,
    tokens_5h=None,
    tokens_week=None,
    retrieval_chunks=20,
    output_tokens=2400,
    per_document_chunks=1000,
)


def resolve_plan_limits(plan_tier: str | PlanTier) -> PlanLimits:
    raw_tier = plan_tier.value if isinstance(plan_tier, PlanTier) else str(plan_tier).strip().lower()
    if raw_tier == PlanTier.INTERNAL.value:
        return INTERNAL_LIMITS
    if raw_tier == PlanTier.PRO.value:
        return PRO_LIMITS
    return FREE_LIMITS


def percentage_used(current: int, limit: int | None) -> float | None:
    if limit in (None, 0):
        return None
    return round((current / limit) * 100, 2)
