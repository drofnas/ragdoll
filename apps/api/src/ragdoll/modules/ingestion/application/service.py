from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.core.config import get_settings
from ragdoll.core.logging import get_logger
from ragdoll.modules.ingestion.domain.policies import (
    build_preview_text,
    chunk_text_with_lines,
    extract_text_content,
    limit_chunks_for_instance,
    mark_processing_stage_completed,
    mark_processing_stage_failed,
    mark_processing_stage_started,
    reset_processing_status_for_stage,
    validate_requested_stage,
)
from ragdoll.modules.ingestion.infrastructure.repository import IngestionRepository
from ragdoll.modules.changes.application.service import record_change_event
from ragdoll.modules.users.application.queries import get_user_by_subject
from ragdoll.platform.db.models import Document, DocumentChunk, Entity
from ragdoll.platform.db.session import get_session_factory
from ragdoll.platform.graph import GraphCleanupService, get_graph_cleanup_service
from ragdoll.platform.llm import (
    DeterministicEntityExtractionService,
    EmbeddingGenerationService,
    EntityExtractionError,
    EntityExtractionService,
    get_embedding_generation_service,
    get_entity_extraction_service,
)
from ragdoll.platform.queues import DocumentProcessingQueueService, ProcessingJobPayload
from ragdoll.platform.storage import DocumentStorageService, get_document_storage
from ragdoll.platform.vector import VectorCleanupService, get_vector_cleanup_service

logger = get_logger("ragdoll.modules.ingestion.service")
AUTO_EXTRACTION_FAILURE_THRESHOLD = 3


def _build_document_chunks(document: Document, *, text: str) -> tuple[int, list[DocumentChunk]]:
    raw_chunks = chunk_text_with_lines(text)
    limited_chunks = limit_chunks_for_instance(raw_chunks)
    rows = [
        DocumentChunk.from_text(
            document_id=document.id,
            space_id=document.space_id,
            chunk_index=index,
            start_line=chunk.start_line,
            text_content=chunk.text,
        )
        for index, chunk in enumerate(limited_chunks)
    ]
    return len(raw_chunks), rows


def _load_document(session: Session, document_id: UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise FileNotFoundError(f"Document {document_id} was not found.")
    return document


def _prepare_document_for_job(
    session: Session,
    *,
    document: Document,
    payload: ProcessingJobPayload,
    storage: DocumentStorageService,
    repo: IngestionRepository,
    vector_cleanup: VectorCleanupService,
    graph_cleanup: GraphCleanupService,
) -> None:
    if not (
        payload.cleanup_derived_artifacts
        or payload.reset_document_content
        or payload.clear_existing_chunks
        or payload.clear_existing_entities
        or payload.cleanup_vectors
        or payload.cleanup_graph
    ):
        return

    document.processing_status = reset_processing_status_for_stage(
        document.processing_status,
        requested_stage=payload.requested_stage,
    )
    if payload.cleanup_derived_artifacts:
        storage.delete_derived_artifacts(document.id)
    if payload.reset_document_content:
        document.preview_text = None
        document.original_text_content = None
        document.chunk_count = 0
        document.indexed_chunk_count = 0
    if payload.clear_existing_chunks:
        repo.replace_chunks(document, [])
    if payload.cleanup_vectors:
        vector_cleanup.cleanup_document(document.id)
    if payload.cleanup_graph:
        graph_cleanup.cleanup_document(document.id)
    if payload.clear_existing_entities:
        repo.clear_entities_for_document(document.id)
        repo.prune_orphan_canonical_entities()
    session.commit()


def _extract_entities(
    session: Session,
    *,
    job_id: UUID,
    document: Document,
    extractor: EntityExtractionService,
    extraction_mode: str,
) -> list[Entity]:
    repo = IngestionRepository(session)
    rows: list[Entity] = []
    chunk_count = len(document.chunks)
    consecutive_failures = 0
    fallback_mode_active = extraction_mode == "deterministic"
    deterministic_extractor = DeterministicEntityExtractionService()

    logger.info(
        "document_id=%s job_id=%s stage=extraction chunk_count=%s mode=%s status=start",
        document.id,
        job_id,
        chunk_count,
        extraction_mode,
    )

    for index, chunk in enumerate(document.chunks, start=1):
        if fallback_mode_active:
            candidates = deterministic_extractor.extract_entities(chunk.text_content)
        else:
            try:
                candidates = extractor.extract_entities(chunk.text_content)
                consecutive_failures = 0
            except (EntityExtractionError, TimeoutError, RuntimeError) as exc:
                if extraction_mode != "auto":
                    logger.warning(
                        "document_id=%s job_id=%s stage=extraction chunk_index=%s mode=%s status=failed error=%s",
                        document.id,
                        job_id,
                        index,
                        extraction_mode,
                        exc,
                    )
                    raise

                consecutive_failures += 1
                logger.warning(
                    "document_id=%s job_id=%s stage=extraction chunk_index=%s mode=auto status=fallback_chunk failure_count=%s error=%s",
                    document.id,
                    job_id,
                    index,
                    consecutive_failures,
                    exc,
                )
                candidates = deterministic_extractor.extract_entities(chunk.text_content)
                if consecutive_failures >= AUTO_EXTRACTION_FAILURE_THRESHOLD and not fallback_mode_active:
                    fallback_mode_active = True
                    logger.warning(
                        "document_id=%s job_id=%s stage=extraction mode=auto status=deterministic_fallback_activated failure_count=%s chunk_count=%s",
                        document.id,
                        job_id,
                        consecutive_failures,
                        chunk_count,
                    )

        for candidate in candidates:
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
    logger.info(
        "document_id=%s job_id=%s stage=extraction chunk_count=%s fallback_activated=%s status=completed",
        document.id,
        job_id,
        chunk_count,
        str(fallback_mode_active).lower(),
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
    settings = get_settings()
    extraction_mode = settings.entity_extraction_mode
    if extraction_mode == "deterministic":
        active_entity_extractor = get_entity_extraction_service()
    active_vector_cleanup = vector_cleanup or get_vector_cleanup_service()
    active_graph_cleanup = graph_cleanup or get_graph_cleanup_service()
    stage_order = ("parsing", "vector", "extraction", "graph")
    current_stage = validate_requested_stage(payload.requested_stage)

    try:
        document = _load_document(session, payload.document_id)
        repo = IngestionRepository(session)
        _prepare_document_for_job(
            session,
            document=document,
            payload=payload,
            storage=active_storage,
            repo=repo,
            vector_cleanup=active_vector_cleanup,
            graph_cleanup=active_graph_cleanup,
        )
        for stage in stage_order:
            if stage_order.index(stage) < stage_order.index(current_stage):
                continue
            current_stage = stage
            document.processing_status = mark_processing_stage_started(document.processing_status, requested_stage=stage)
            session.commit()

            if stage == "parsing":
                blob = active_storage.download_original_file(document.storage_key)
                extracted_text = extract_text_content(file_type=document.file_type, content=blob)
                get_user_by_subject(session, str(document.uploaded_by))
                total_chunks, chunk_rows = _build_document_chunks(document, text=extracted_text)
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
                entities = _extract_entities(
                    session,
                    job_id=payload.job_id,
                    document=document,
                    extractor=active_entity_extractor,
                    extraction_mode=extraction_mode,
                )
                repo.replace_entities(document, entities)
                session.flush()
                repo.prune_orphan_canonical_entities()
            elif stage == "graph":
                active_graph_cleanup.project_document_relationships(session, document=document)

            document.processing_status = mark_processing_stage_completed(document.processing_status, completed_stage=stage)
            session.commit()

        queue.mark_job_completed(payload.job_id)
        event_type = "document_processed" if payload.job_kind == "upload" else "document_reprocessed"
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
        session.rollback()
        try:
            document = session.get(Document, payload.document_id)
            if document is not None:
                document.processing_status = mark_processing_stage_failed(
                    document.processing_status,
                    failed_stage=current_stage,
                    detail=str(exc),
                )
                session.commit()
        except Exception:
            session.rollback()
        finally:
            queue.mark_job_failed(payload.job_id, str(exc))
    finally:
        session.close()
