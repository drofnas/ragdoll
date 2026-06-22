from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.modules.ingestion.domain.policies import (
    build_preview_text,
    chunk_text,
    extract_text_content,
    limit_chunks_for_plan,
    mark_processing_stage_completed,
    mark_processing_stage_failed,
    mark_processing_stage_started,
    validate_requested_stage,
)
from ragdoll.modules.ingestion.infrastructure.repository import IngestionRepository
from ragdoll.modules.changes.application.service import record_change_event
from ragdoll.modules.users.application.queries import get_user_by_subject
from ragdoll.platform.db.models import Document, DocumentChunk, Entity
from ragdoll.platform.db.session import get_session_factory
from ragdoll.platform.graph import GraphCleanupService, get_graph_cleanup_service
from ragdoll.platform.llm import (
    EmbeddingGenerationService,
    EntityExtractionService,
    get_embedding_generation_service,
    get_entity_extraction_service,
)
from ragdoll.platform.queues import DocumentProcessingQueueService, ProcessingJobPayload
from ragdoll.platform.storage import DocumentStorageService, get_document_storage
from ragdoll.platform.vector import VectorCleanupService, get_vector_cleanup_service


def _build_document_chunks(document: Document, *, text: str, plan_tier: str) -> tuple[int, list[DocumentChunk]]:
    raw_chunks = chunk_text(text)
    limited_chunks = limit_chunks_for_plan(raw_chunks, plan_tier=plan_tier)
    rows = [
        DocumentChunk.from_text(
            document_id=document.id,
            space_id=document.space_id,
            chunk_index=index,
            text_content=chunk,
        )
        for index, chunk in enumerate(limited_chunks)
    ]
    return len(raw_chunks), rows


def _load_document(session: Session, document_id: UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise FileNotFoundError(f"Document {document_id} was not found.")
    return document


def _extract_entities(
    session: Session,
    *,
    document: Document,
    extractor: EntityExtractionService,
) -> list[Entity]:
    repo = IngestionRepository(session)
    rows: list[Entity] = []
    for chunk in document.chunks:
        for candidate in extractor.extract_entities(chunk.text_content):
            canonical = repo.get_or_create_canonical_entity(
                space_id=document.space_id,
                entity_type=candidate.entity_type,
                normalized_name=candidate.normalized_name,
                display_name=candidate.surface_text,
            )
            rows.append(
                Entity(
                    space_id=document.space_id,
                    document_id=document.id,
                    chunk_id=chunk.id,
                    canonical_entity_id=canonical.id,
                    entity_type=candidate.entity_type,
                    surface_text=candidate.surface_text[:255],
                    normalized_name=candidate.normalized_name[:255],
                    confidence_score=candidate.confidence_score,
                    extraction_model=None,
                    extraction_metadata={"source": "worker_pipeline"},
                )
            )
    return rows


def process_job_payload(
    payload: ProcessingJobPayload,
    queue: DocumentProcessingQueueService,
    *,
    storage: DocumentStorageService | None = None,
    embedding_service: EmbeddingGenerationService | None = None,
    entity_extraction_service: EntityExtractionService | None = None,
    vector_cleanup: VectorCleanupService | None = None,
    graph_cleanup: GraphCleanupService | None = None,
) -> None:
    session = get_session_factory()()
    active_storage = storage or get_document_storage()
    active_embedding_service = embedding_service or get_embedding_generation_service()
    active_entity_extractor = entity_extraction_service or get_entity_extraction_service()
    active_vector_cleanup = vector_cleanup or get_vector_cleanup_service()
    active_graph_cleanup = graph_cleanup or get_graph_cleanup_service()
    stage_order = ("parsing", "vector", "extraction", "graph")
    current_stage = validate_requested_stage(payload.requested_stage)

    try:
        document = _load_document(session, payload.document_id)
        repo = IngestionRepository(session)
        for stage in stage_order:
            if stage_order.index(stage) < stage_order.index(current_stage):
                continue
            current_stage = stage
            document.processing_status = mark_processing_stage_started(document.processing_status, requested_stage=stage)
            session.commit()

            if stage == "parsing":
                blob = active_storage.download_original_file(document.storage_key)
                extracted_text = extract_text_content(file_type=document.file_type, content=blob)
                user = get_user_by_subject(session, str(document.uploaded_by))
                total_chunks, chunk_rows = _build_document_chunks(document, text=extracted_text, plan_tier=user.plan_tier)
                repo.replace_chunks(document, chunk_rows)
                session.flush()
                document.preview_text = build_preview_text(extracted_text)
                document.original_text_content = extracted_text
                document.chunk_count = total_chunks
                document.indexed_chunk_count = len(chunk_rows)
            elif stage == "vector":
                chunks = list(document.chunks)
                if not chunks:
                    raise ValueError("Vector projection requires parsed document chunks.")
                embeddings = active_embedding_service.generate_embeddings([chunk.text_content for chunk in chunks])
                active_vector_cleanup.replace_document_embeddings(
                    session,
                    document=document,
                    chunks=chunks,
                    embeddings=embeddings,
                    embedding_model=getattr(active_embedding_service, "_model", "deterministic"),
                )
            elif stage == "extraction":
                entities = _extract_entities(session, document=document, extractor=active_entity_extractor)
                repo.replace_entities(document, entities)
                session.flush()
                repo.prune_orphan_canonical_entities()
            elif stage == "graph":
                active_graph_cleanup.project_document_relationships(session, document=document)

            document.processing_status = mark_processing_stage_completed(document.processing_status, completed_stage=stage)
            session.commit()

        queue.mark_job_completed(payload.job_id)
        event_type = "document_processed" if payload.attempt == 1 and payload.requested_stage == "parsing" else "document_reprocessed"
        record_change_event(
            session,
            space_id=document.space_id,
            event_type=event_type,
            title="Document processed" if event_type == "document_processed" else "Document reprocessed",
            summary=f"{document.title} completed {payload.requested_stage} processing.",
            actor_user_id=document.uploaded_by,
            document_id=document.id,
            payload={"requested_stage": payload.requested_stage, "attempt": payload.attempt},
        )
        session.commit()
    except Exception as exc:
        document = session.get(Document, payload.document_id)
        if document is not None:
            document.processing_status = mark_processing_stage_failed(
                document.processing_status,
                failed_stage=current_stage,
                detail=str(exc),
            )
            session.commit()
        queue.mark_job_failed(payload.job_id, str(exc))
    finally:
        session.close()
