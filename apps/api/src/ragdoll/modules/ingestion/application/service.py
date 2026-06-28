from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from ragdoll.core.config import get_settings
from ragdoll.core.logging import get_logger
from ragdoll.modules.changes.application.service import record_change_event
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
from ragdoll.modules.pinned_facts.application.service import recheck_space_facts
from ragdoll.modules.users.application.queries import get_user_by_subject
from ragdoll.platform.db.models import Document, DocumentChunk, DocumentProcessingJob, Entity
from ragdoll.platform.db.session import get_session_factory
from ragdoll.platform.graph import GraphCleanupService, get_graph_cleanup_service
from ragdoll.platform.llm import (
    ChunkExtractionRequest,
    ChunkExtractionResult,
    DeterministicEntityExtractionService,
    EmbeddingGenerationService,
    EntityExtractionError,
    EntityExtractionService,
    get_embedding_generation_service,
    get_entity_extraction_service,
)
from ragdoll.platform.queues import ProcessingJobPayload, utc_now
from ragdoll.platform.storage import DocumentStorageService, get_document_storage
from ragdoll.platform.vector import VectorCleanupService, get_vector_cleanup_service

logger = get_logger("ragdoll.modules.ingestion.service")
AUTO_EXTRACTION_FAILURE_THRESHOLD = 3


def _save_job_meta(current_job: Any | None, **updates: object) -> None:
    if current_job is None:
        return
    meta = dict(getattr(current_job, "meta", {}) or {})
    meta.update(updates)
    meta["updated_at"] = utc_now().isoformat()
    current_job.meta = meta
    current_job.save_meta()


def _set_sql_job_processing(session: Session, job_id: UUID) -> None:
    job = session.get(DocumentProcessingJob, job_id)
    if job is None:
        raise FileNotFoundError(f"Document processing job {job_id} was not found.")
    if job.status == "completed":
        return
    job.status = "processing"
    job.started_at = job.started_at or utc_now()
    job.completed_at = None
    job.visible_error_detail = None
    session.commit()


def _set_sql_job_completed(session: Session, job_id: UUID) -> None:
    job = session.get(DocumentProcessingJob, job_id)
    if job is None:
        return
    job.status = "completed"
    job.completed_at = utc_now()
    job.visible_error_detail = None
    session.commit()


def _set_sql_job_failed(session: Session, job_id: UUID, detail: str) -> None:
    job = session.get(DocumentProcessingJob, job_id)
    if job is None:
        return
    job.status = "failed"
    job.completed_at = utc_now()
    job.visible_error_detail = detail[:2000]
    session.commit()


def _update_stage_progress(
    current_job: Any | None,
    *,
    stage: str,
    current: int,
    total: int,
    detail: str | None = None,
) -> None:
    _save_job_meta(
        current_job,
        stage=stage,
        detail=detail,
        chunk_progress_current=current,
        chunk_progress_total=total,
    )


def _build_document_chunks(
    document: Document,
    *,
    text: str,
    on_chunk_built: Callable[[int, int], None] | None = None,
) -> tuple[int, list[DocumentChunk]]:
    raw_chunks = chunk_text_with_lines(text)
    limited_chunks = limit_chunks_for_instance(raw_chunks)
    rows: list[DocumentChunk] = []
    total_chunks = len(limited_chunks)
    for index, chunk in enumerate(limited_chunks):
        rows.append(
            DocumentChunk.from_text(
                document_id=document.id,
                space_id=document.space_id,
                chunk_index=index,
                start_line=chunk.start_line,
                text_content=chunk.text,
            )
        )
        if on_chunk_built is not None:
            on_chunk_built(index + 1, total_chunks)
    return len(raw_chunks), rows


def _load_document(session: Session, document_id: UUID) -> Document:
    document = session.get(Document, document_id)
    if document is None:
        raise FileNotFoundError(f"Document {document_id} was not found.")
    return document


def _chunk_batch(items: list[ChunkExtractionRequest], batch_size: int) -> list[list[ChunkExtractionRequest]]:
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def _chunk_rows_batch(items: list[DocumentChunk], batch_size: int) -> list[list[DocumentChunk]]:
    return [items[index : index + batch_size] for index in range(0, len(items), batch_size)]


def _run_deterministic_extraction_batch(
    extractor: DeterministicEntityExtractionService,
    batch: list[ChunkExtractionRequest],
) -> list[ChunkExtractionResult]:
    return extractor.extract_entities_batch(batch)


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
    if payload.cleanup_vectors:
        vector_cleanup.cleanup_document(document.id)
    if payload.cleanup_graph:
        graph_cleanup.cleanup_document(document.id)
    if payload.clear_existing_entities:
        repo.clear_entities_for_document(document.id)
        repo.prune_orphan_canonical_entities()
    if payload.reset_document_content:
        document.preview_text = None
        document.original_text_content = None
        document.chunk_count = 0
        document.indexed_chunk_count = 0
    if payload.clear_existing_chunks:
        repo.replace_chunks(document, [])
    session.commit()


def _extract_entities(
    session: Session,
    *,
    job_id: UUID,
    document: Document,
    extractor: EntityExtractionService,
    extraction_mode: str,
    extraction_batch_size: int,
    max_parallel_batches: int,
    current_job: Any | None = None,
) -> list[Entity]:
    repo = IngestionRepository(session)
    rows: list[Entity] = []
    chunks = list(document.chunks)
    chunk_count = len(chunks)
    consecutive_failures = 0
    fallback_mode_active = extraction_mode == "deterministic"
    deterministic_extractor = DeterministicEntityExtractionService()
    chunk_requests = [
        ChunkExtractionRequest(chunk_index=chunk.chunk_index, text=chunk.text_content)
        for chunk in chunks
    ]
    chunk_by_index = {chunk.chunk_index: chunk for chunk in chunks}
    extraction_results: dict[int, ChunkExtractionResult] = {}
    extraction_metadata_by_index: dict[int, dict[str, object]] = {}
    chunk_batches = _chunk_batch(chunk_requests, extraction_batch_size)

    logger.info(
        "document_id=%s job_id=%s stage=extraction chunk_count=%s mode=%s batch_size=%s max_parallel_batches=%s status=start",
        document.id,
        job_id,
        chunk_count,
        extraction_mode,
        extraction_batch_size,
        max_parallel_batches,
    )
    _update_stage_progress(current_job, stage="extraction", current=0, total=chunk_count)

    processed_chunk_count = 0

    for offset in range(0, len(chunk_batches), max_parallel_batches):
        batch_window = chunk_batches[offset : offset + max_parallel_batches]
        if fallback_mode_active:
            for batch in batch_window:
                batch_results = _run_deterministic_extraction_batch(deterministic_extractor, batch)
                for result in batch_results:
                    extraction_results[result.chunk_index] = result
                    extraction_metadata_by_index[result.chunk_index] = {
                        "source": "worker_pipeline",
                        "chunk_index": result.chunk_index,
                        "extraction_mode": "deterministic",
                        "batch_size": len(batch),
                    }
                processed_chunk_count += len(batch)
                _update_stage_progress(
                    current_job,
                    stage="extraction",
                    current=processed_chunk_count,
                    total=chunk_count,
                )
            continue

        with ThreadPoolExecutor(max_workers=max_parallel_batches) as executor:
            future_by_batch: list[tuple[list[ChunkExtractionRequest], Future[list[ChunkExtractionResult]]]] = [
                (batch, executor.submit(extractor.extract_entities_batch, batch))
                for batch in batch_window
            ]

            for batch, future in future_by_batch:
                chunk_indexes = [chunk.chunk_index for chunk in batch]
                try:
                    batch_results = future.result()
                    consecutive_failures = 0
                    for result in batch_results:
                        extraction_results[result.chunk_index] = result
                        extraction_metadata_by_index[result.chunk_index] = {
                            "source": "worker_pipeline",
                            "chunk_index": result.chunk_index,
                            "extraction_mode": extraction_mode,
                            "batch_size": len(batch),
                        }
                    processed_chunk_count += len(batch)
                    _update_stage_progress(
                        current_job,
                        stage="extraction",
                        current=processed_chunk_count,
                        total=chunk_count,
                    )
                except (EntityExtractionError, TimeoutError, RuntimeError) as exc:
                    if extraction_mode != "auto":
                        logger.warning(
                            "document_id=%s job_id=%s stage=extraction chunk_indexes=%s mode=%s status=failed error=%s",
                            document.id,
                            job_id,
                            chunk_indexes,
                            extraction_mode,
                            exc,
                        )
                        raise

                    consecutive_failures += 1
                    logger.warning(
                        "document_id=%s job_id=%s stage=extraction chunk_indexes=%s mode=auto status=fallback_batch failure_count=%s error=%s",
                        document.id,
                        job_id,
                        chunk_indexes,
                        consecutive_failures,
                        exc,
                    )
                    batch_results = _run_deterministic_extraction_batch(deterministic_extractor, batch)
                    for result in batch_results:
                        extraction_results[result.chunk_index] = result
                        extraction_metadata_by_index[result.chunk_index] = {
                            "source": "worker_pipeline",
                            "chunk_index": result.chunk_index,
                            "extraction_mode": "deterministic",
                            "batch_size": len(batch),
                        }
                    processed_chunk_count += len(batch)
                    _update_stage_progress(
                        current_job,
                        stage="extraction",
                        current=processed_chunk_count,
                        total=chunk_count,
                    )
                    if consecutive_failures >= AUTO_EXTRACTION_FAILURE_THRESHOLD and not fallback_mode_active:
                        fallback_mode_active = True
                        logger.warning(
                            "document_id=%s job_id=%s stage=extraction mode=auto status=deterministic_fallback_activated failure_count=%s chunk_count=%s",
                            document.id,
                            job_id,
                            consecutive_failures,
                            chunk_count,
                        )

    for chunk_index in sorted(extraction_results):
        chunk = chunk_by_index[chunk_index]
        candidates = extraction_results[chunk_index].entities
        extraction_metadata = extraction_metadata_by_index[chunk_index]
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
                    extraction_metadata=extraction_metadata,
                )
            )
    logger.info(
        "document_id=%s job_id=%s stage=extraction chunk_count=%s fallback_activated=%s status=completed",
        document.id,
        job_id,
        chunk_count,
        str(fallback_mode_active).lower(),
    )
    _update_stage_progress(current_job, stage="extraction", current=chunk_count, total=chunk_count)
    return rows


def process_job_payload(
    payload: ProcessingJobPayload,
    *,
    storage: DocumentStorageService | None = None,
    embedding_service: EmbeddingGenerationService | None = None,
    entity_extraction_service: EntityExtractionService | None = None,
    vector_cleanup: VectorCleanupService | None = None,
    graph_cleanup: GraphCleanupService | None = None,
    current_job: Any | None = None,
) -> None:
    session = get_session_factory()()
    active_storage = storage or get_document_storage()
    active_embedding_service = embedding_service or get_embedding_generation_service()
    active_entity_extractor = entity_extraction_service or get_entity_extraction_service()
    settings = get_settings()
    extraction_mode = settings.entity_extraction_mode
    extraction_batch_size = settings.entity_extraction_batch_size
    max_parallel_batches = settings.entity_extraction_max_parallel_batches
    if extraction_mode == "deterministic":
        active_entity_extractor = get_entity_extraction_service()
    active_vector_cleanup = vector_cleanup or get_vector_cleanup_service()
    active_graph_cleanup = graph_cleanup or get_graph_cleanup_service()
    stage_order = ("parsing", "vector", "extraction", "graph")
    current_stage = validate_requested_stage(payload.requested_stage)

    try:
        _set_sql_job_processing(session, payload.job_id)
        document = _load_document(session, payload.document_id)
        repo = IngestionRepository(session)
        _update_stage_progress(current_job, stage=current_stage, current=0, total=document.chunk_count)
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
            stage_total = 0 if stage == "parsing" else len(list(document.chunks))
            _update_stage_progress(current_job, stage=stage, current=0, total=stage_total)

            if stage == "parsing":
                blob = active_storage.download_original_file(document.storage_key)
                extracted_text = extract_text_content(file_type=document.file_type, content=blob)
                get_user_by_subject(session, str(document.uploaded_by))
                total_chunks, chunk_rows = _build_document_chunks(
                    document,
                    text=extracted_text,
                    on_chunk_built=(
                        lambda current, total: _update_stage_progress(
                            current_job,
                            stage="parsing",
                            current=current,
                            total=total,
                        )
                    ),
                )
                repo.replace_chunks(document, chunk_rows)
                session.flush()
                document.preview_text = build_preview_text(extracted_text)
                document.original_text_content = extracted_text
                document.chunk_count = total_chunks
                document.indexed_chunk_count = len(chunk_rows)
                _update_stage_progress(
                    current_job,
                    stage="parsing",
                    current=len(chunk_rows),
                    total=len(chunk_rows),
                )
            elif stage == "vector":
                chunks = list(document.chunks)
                if not chunks:
                    raise ValueError("Vector projection requires parsed document chunks.")
                vector_total = len(chunks)
                _update_stage_progress(current_job, stage="vector", current=0, total=vector_total)
                embeddings: list[list[float]] = []
                processed_vector_chunks = 0
                for chunk_batch in _chunk_rows_batch(chunks, extraction_batch_size):
                    embeddings.extend(
                        active_embedding_service.generate_embeddings(
                            [chunk.text_content for chunk in chunk_batch]
                        )
                    )
                    processed_vector_chunks += len(chunk_batch)
                    _update_stage_progress(
                        current_job,
                        stage="vector",
                        current=processed_vector_chunks,
                        total=vector_total,
                    )
                active_vector_cleanup.replace_document_embeddings(
                    session,
                    document=document,
                    chunks=chunks,
                    embeddings=embeddings,
                    embedding_model=getattr(active_embedding_service, "_model", "deterministic"),
                )
                _update_stage_progress(current_job, stage="vector", current=vector_total, total=vector_total)
            elif stage == "extraction":
                entities = _extract_entities(
                    session,
                    job_id=payload.job_id,
                    document=document,
                    extractor=active_entity_extractor,
                    extraction_mode=extraction_mode,
                    extraction_batch_size=extraction_batch_size,
                    max_parallel_batches=max_parallel_batches,
                    current_job=current_job,
                )
                repo.replace_entities(document, entities)
                session.flush()
                repo.prune_orphan_canonical_entities()
            elif stage == "graph":
                graph_total = len(list(document.chunks))
                _update_stage_progress(current_job, stage="graph", current=0, total=graph_total)
                active_graph_cleanup.project_document_relationships(
                    session,
                    document=document,
                    on_chunk_processed=(
                        lambda current, total: _update_stage_progress(
                            current_job,
                            stage="graph",
                            current=current,
                            total=total,
                        )
                    ),
                )

            document.processing_status = mark_processing_stage_completed(document.processing_status, completed_stage=stage)
            session.commit()

        _set_sql_job_completed(session, payload.job_id)
        _update_stage_progress(
            current_job,
            stage=current_stage,
            current=document.indexed_chunk_count,
            total=document.indexed_chunk_count,
        )
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
        recheck_space_facts(session, str(document.uploaded_by), space_id=document.space_id, document_id=document.id)
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
            _set_sql_job_failed(session, payload.job_id, str(exc))
            _update_stage_progress(
                current_job,
                stage=current_stage,
                current=0,
                total=getattr(document, "indexed_chunk_count", 0) if "document" in locals() else 0,
                detail=str(exc),
            )
    finally:
        session.close()
