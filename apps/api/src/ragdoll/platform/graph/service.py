from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol
from uuid import UUID

from ragdoll.core.config import get_settings


class GraphCleanupService(Protocol):
    """Delete or tombstone graph projections for one document."""

    def cleanup_document(self, document_id: UUID) -> bool: ...


@dataclass
class InMemoryGraphCleanupService:
    cleaned_document_ids: set[UUID] = field(default_factory=set)

    def cleanup_document(self, document_id: UUID) -> bool:
        already_cleaned = document_id in self.cleaned_document_ids
        self.cleaned_document_ids.add(document_id)
        return not already_cleaned


class NoopGraphCleanupService:
    def cleanup_document(self, document_id: UUID) -> bool:
        del document_id
        return False


@lru_cache(maxsize=1)
def get_graph_cleanup_service() -> GraphCleanupService:
    settings = get_settings()
    if settings.e2e_memory_backends:
        return InMemoryGraphCleanupService()
    return NoopGraphCleanupService()
