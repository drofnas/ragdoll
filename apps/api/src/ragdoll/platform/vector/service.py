from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from ragdoll.core.config import get_settings
from ragdoll.platform.db.models import Document, DocumentChunk, DocumentChunkVector
from ragdoll.platform.db.session import get_session_factory


class VectorCleanupService(Protocol):
    """Delete document-derived vector artifacts and replace chunk embeddings."""

    def cleanup_document(self, document_id: UUID) -> bool: ...

    def replace_document_embeddings(
        self,
        session: Session,
        *,
        document: Document,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        embedding_model: str,
    ) -> int: ...


@dataclass
class InMemoryVectorCleanupService:
    cleaned_document_ids: set[UUID] = field(default_factory=set)
    stored_vectors: dict[UUID, DocumentChunkVector] = field(default_factory=dict)

    def cleanup_document(self, document_id: UUID) -> bool:
        already_cleaned = document_id in self.cleaned_document_ids
        self.cleaned_document_ids.add(document_id)
        for chunk_id in [chunk_id for chunk_id, row in self.stored_vectors.items() if row.document_id == document_id]:
            self.stored_vectors.pop(chunk_id, None)
        return not already_cleaned

    def replace_document_embeddings(
        self,
        session: Session,
        *,
        document: Document,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        embedding_model: str,
    ) -> int:
        del session
        for chunk in chunks:
            self.stored_vectors.pop(chunk.id, None)
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self.stored_vectors[chunk.id] = DocumentChunkVector(
                chunk_id=chunk.id,
                document_id=document.id,
                space_id=document.space_id,
                chunk_index=chunk.chunk_index,
                checksum=chunk.checksum,
                embedding_model=embedding_model,
                embedding_dimensions=len(embedding),
                embedding=embedding,
            )
        return len(chunks)


class SqlVectorCleanupService:
    def cleanup_document(self, document_id: UUID) -> bool:
        session = get_session_factory()()
        try:
            result = session.execute(delete(DocumentChunkVector).where(DocumentChunkVector.document_id == document_id))
            session.commit()
            return bool(result.rowcount)
        finally:
            session.close()

    def replace_document_embeddings(
        self,
        session: Session,
        *,
        document: Document,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
        embedding_model: str,
    ) -> int:
        session.execute(delete(DocumentChunkVector).where(DocumentChunkVector.document_id == document.id))
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            session.add(
                DocumentChunkVector(
                    chunk_id=chunk.id,
                    document_id=document.id,
                    space_id=document.space_id,
                    chunk_index=chunk.chunk_index,
                    checksum=chunk.checksum,
                    embedding_model=embedding_model,
                    embedding_dimensions=len(embedding),
                    embedding=embedding,
                )
            )
        return len(chunks)


@lru_cache(maxsize=1)
def get_vector_cleanup_service() -> VectorCleanupService:
    settings = get_settings()
    if settings.e2e_memory_backends:
        return InMemoryVectorCleanupService()
    return SqlVectorCleanupService()
