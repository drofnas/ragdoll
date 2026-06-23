from __future__ import annotations

from dataclasses import dataclass

from ragdoll.core.config import Settings, get_settings


@dataclass(frozen=True)
class InstanceLimits:
    documents: int | None
    max_file_size_bytes: int | None
    chunks: int | None
    storage_bytes: int | None
    tokens_5h: int | None
    tokens_week: int | None
    retrieval_chunks: int
    output_tokens: int
    per_document_chunks: int


def resolve_instance_limits(settings: Settings | None = None) -> InstanceLimits:
    runtime_settings = settings or get_settings()
    return InstanceLimits(
        documents=runtime_settings.instance_limit_documents,
        max_file_size_bytes=runtime_settings.instance_limit_max_file_size_bytes,
        chunks=runtime_settings.instance_limit_chunks,
        storage_bytes=runtime_settings.instance_limit_storage_bytes,
        tokens_5h=runtime_settings.instance_limit_tokens_5h,
        tokens_week=runtime_settings.instance_limit_tokens_week,
        retrieval_chunks=runtime_settings.instance_limit_retrieval_chunks,
        output_tokens=runtime_settings.instance_limit_output_tokens,
        per_document_chunks=runtime_settings.instance_limit_per_document_chunks,
    )
