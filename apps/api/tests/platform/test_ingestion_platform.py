from __future__ import annotations

import pytest

from ragdoll.core.config import get_settings
from ragdoll.modules.ingestion.domain.policies import build_processing_status_for_upload
from ragdoll.platform.db.models import Document, DocumentChunk, DocumentProcessingJob, DocumentChunkVector, Entity, GraphEdge, Space, User
from ragdoll.platform.llm import (
    ChunkExtractionRequest,
    ChunkExtractionResult,
    DeterministicEmbeddingService,
    DeterministicEntityExtractionService,
    get_entity_extraction_service,
)
from ragdoll.platform.queues import InMemoryDocumentProcessingQueue, ProcessingJobPayload, SqlDocumentProcessingQueue
from ragdoll.platform.storage import InMemoryDocumentStorage
from ragdoll.workers.document_pipeline import drain_document_jobs


@pytest.fixture(autouse=True)
def clear_entity_extraction_caches():
    yield
    get_settings.cache_clear()
    get_entity_extraction_service.cache_clear()


def _seed_user_space_document(db_session):
    user = User(email="worker@example.com", hashed_password="hashed")
    db_session.add(user)
    db_session.flush()
    space = Space(owner_user_id=user.id, name="Default", description=None, is_default=True)
    db_session.add(space)
    db_session.flush()
    document = Document(
        space_id=space.id,
        uploaded_by=user.id,
        title="notes.txt",
        original_filename="notes.txt",
        mime_type="text/plain",
        file_type="txt",
        file_size=12,
        storage_key=f"documents/{user.id}/{space.id}/notes.txt",
        source_kind="manual_upload",
        processing_status=build_processing_status_for_upload(),
    )
    db_session.add(document)
    db_session.flush()
    return user, space, document


def test_sql_queue_claims_and_marks_completion(db_session):
    user, space, document = _seed_user_space_document(db_session)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="parsing",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.commit()

    queue = SqlDocumentProcessingQueue()
    payload = queue.claim_next_job()
    assert payload is not None
    assert payload.document_id == document.id

    queue.mark_job_completed(job.id)
    db_session.expire_all()
    refreshed = db_session.get(DocumentProcessingJob, job.id)
    assert refreshed is not None
    assert refreshed.status == "completed"
    assert refreshed.completed_at is not None


def test_worker_marks_document_failed_when_blob_is_missing(db_session):
    user, space, document = _seed_user_space_document(db_session)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="parsing",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.commit()

    queue = InMemoryDocumentProcessingQueue()
    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=space.id,
            uploaded_by=user.id,
            requested_stage="parsing",
            attempt=1,
        )
    )
    assert (
        drain_document_jobs(
            queue=queue,
            storage=InMemoryDocumentStorage(),
            embedding_service=DeterministicEmbeddingService(),
            entity_extraction_service=DeterministicEntityExtractionService(),
        )
        == 1
    )
    db_session.expire_all()
    refreshed_document = db_session.get(Document, document.id)
    refreshed_job = db_session.get(DocumentProcessingJob, job.id)
    assert refreshed_document is not None
    assert refreshed_document.processing_status["overall"] == "failed"
    assert refreshed_job is not None
    assert refreshed_job.status == "failed"


def test_worker_replaces_existing_chunks_idempotently(db_session):
    user, space, document = _seed_user_space_document(db_session)
    existing_chunk = DocumentChunk.from_text(
        document_id=document.id,
        space_id=space.id,
        chunk_index=0,
        text_content="stale chunk",
    )
    db_session.add(existing_chunk)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="parsing",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.commit()

    storage = InMemoryDocumentStorage()
    storage.store_original_file(document.storage_key, b"fresh content for parsing")
    queue = InMemoryDocumentProcessingQueue()
    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=space.id,
            uploaded_by=user.id,
            requested_stage="parsing",
            attempt=1,
        )
    )
    assert (
        drain_document_jobs(
            queue=queue,
            storage=storage,
            embedding_service=DeterministicEmbeddingService(),
            entity_extraction_service=DeterministicEntityExtractionService(),
        )
        == 1
    )
    db_session.expire_all()
    chunks = db_session.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).all()
    assert len(chunks) == 1
    assert chunks[0].text_content == "fresh content for parsing"


class FailingEmbeddingService:
    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        del texts
        raise RuntimeError("embedding outage")


class FailingEntityExtractionService:
    def extract_entities_batch(self, chunks: list[ChunkExtractionRequest]):
        del chunks
        raise RuntimeError("entity extraction outage")


class CountingEntityExtractionService:
    def __init__(self, *, failure_count: int = 0) -> None:
        self.failure_count = failure_count
        self.call_count = 0

    def extract_entities_batch(self, chunks: list[ChunkExtractionRequest]):
        self.call_count += 1
        if self.call_count <= self.failure_count:
            raise RuntimeError("entity extraction outage")
        return DeterministicEntityExtractionService().extract_entities_batch(chunks)


class ReverseBatchEntityExtractionService:
    def __init__(self) -> None:
        self.call_count = 0

    def extract_entities_batch(self, chunks: list[ChunkExtractionRequest]):
        self.call_count += 1
        results = []
        for chunk in chunks:
            results.append(
                ChunkExtractionResult(
                    chunk_index=chunk.chunk_index,
                    entities=[
                        DeterministicEntityExtractionService().extract_entities(
                            f"Project Atlas Chunk {chunk.chunk_index}"
                        )[0]
                    ],
                )
            )
        return list(reversed(results))


def _set_entity_extraction_mode(monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    monkeypatch.setenv("ENTITY_EXTRACTION_MODE", mode)
    get_settings.cache_clear()
    get_entity_extraction_service.cache_clear()


def _set_entity_extraction_batch_settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    batch_size: int,
    max_parallel_batches: int,
) -> None:
    monkeypatch.setenv("ENTITY_EXTRACTION_BATCH_SIZE", str(batch_size))
    monkeypatch.setenv("ENTITY_EXTRACTION_MAX_PARALLEL_BATCHES", str(max_parallel_batches))
    get_settings.cache_clear()
    get_entity_extraction_service.cache_clear()


def _seed_document_chunks(db_session, document: Document, *, chunk_count: int) -> None:
    db_session.add_all(
        [
            DocumentChunk.from_text(
                document_id=document.id,
                space_id=document.space_id,
                chunk_index=index,
                text_content=f"Project Atlas chunk {index}",
            )
            for index in range(chunk_count)
        ]
    )
    document.chunk_count = chunk_count
    document.indexed_chunk_count = chunk_count
    document.processing_status = {
        "overall": "processing",
        "upload": "completed",
        "parsing": "completed",
        "vector": "completed",
        "extraction": "pending",
        "graph": "pending",
        "detail": None,
    }
    db_session.commit()


@pytest.mark.parametrize(
    ("embedding_service", "entity_extraction_service", "failed_stage", "expected_completed_stage"),
    [
        (FailingEmbeddingService(), DeterministicEntityExtractionService(), "vector", "parsing"),
        (DeterministicEmbeddingService(), FailingEntityExtractionService(), "extraction", "vector"),
    ],
)
def test_worker_marks_stage_specific_failures(
    db_session,
    monkeypatch,
    embedding_service,
    entity_extraction_service,
    failed_stage,
    expected_completed_stage,
):
    if failed_stage == "extraction":
        _set_entity_extraction_mode(monkeypatch, "ollama")
    user, space, document = _seed_user_space_document(db_session)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="parsing",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.commit()

    storage = InMemoryDocumentStorage()
    storage.store_original_file(document.storage_key, b"Project Atlas works with Ragdoll")
    queue = InMemoryDocumentProcessingQueue()
    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=space.id,
            uploaded_by=user.id,
            requested_stage="parsing",
            attempt=1,
        )
    )

    assert (
        drain_document_jobs(
            queue=queue,
            storage=storage,
            embedding_service=embedding_service,
            entity_extraction_service=entity_extraction_service,
        )
        == 1
    )

    db_session.expire_all()
    refreshed_document = db_session.get(Document, document.id)
    refreshed_job = db_session.get(DocumentProcessingJob, job.id)
    assert refreshed_document is not None
    assert refreshed_job is not None
    assert refreshed_document.processing_status["overall"] == "failed"
    assert refreshed_document.processing_status[failed_stage] == "failed"
    assert refreshed_document.processing_status[expected_completed_stage] == "completed"
    assert refreshed_job.status == "failed"


def test_worker_deterministic_mode_skips_primary_entity_extractor(db_session, monkeypatch):
    _set_entity_extraction_mode(monkeypatch, "deterministic")
    user, space, document = _seed_user_space_document(db_session)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="parsing",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.commit()

    storage = InMemoryDocumentStorage()
    storage.store_original_file(document.storage_key, b"Project Atlas works with Ragdoll")
    queue = InMemoryDocumentProcessingQueue()
    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=space.id,
            uploaded_by=user.id,
            requested_stage="parsing",
            attempt=1,
        )
    )
    primary_extractor = CountingEntityExtractionService(failure_count=1)

    assert (
        drain_document_jobs(
            queue=queue,
            storage=storage,
            embedding_service=DeterministicEmbeddingService(),
            entity_extraction_service=primary_extractor,
        )
        == 1
    )

    db_session.expire_all()
    refreshed_document = db_session.get(Document, document.id)
    refreshed_job = db_session.get(DocumentProcessingJob, job.id)
    assert primary_extractor.call_count == 0
    assert refreshed_document is not None
    assert refreshed_document.processing_status["overall"] == "completed"
    assert refreshed_job is not None
    assert refreshed_job.status == "completed"


def test_worker_auto_mode_switches_to_deterministic_after_three_failures(db_session, monkeypatch):
    _set_entity_extraction_mode(monkeypatch, "auto")
    _set_entity_extraction_batch_settings(monkeypatch, batch_size=2, max_parallel_batches=1)
    user, space, document = _seed_user_space_document(db_session)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="extraction",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.flush()
    _seed_document_chunks(db_session, document, chunk_count=8)

    queue = InMemoryDocumentProcessingQueue()
    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=space.id,
            uploaded_by=user.id,
            requested_stage="extraction",
            attempt=1,
        )
    )
    primary_extractor = CountingEntityExtractionService(failure_count=3)

    assert (
        drain_document_jobs(
            queue=queue,
            storage=InMemoryDocumentStorage(),
            embedding_service=DeterministicEmbeddingService(),
            entity_extraction_service=primary_extractor,
        )
        == 1
    )

    db_session.expire_all()
    refreshed_document = db_session.get(Document, document.id)
    refreshed_job = db_session.get(DocumentProcessingJob, job.id)
    assert primary_extractor.call_count == 3
    assert refreshed_document is not None
    assert refreshed_document.processing_status["overall"] == "completed"
    assert refreshed_document.chunk_count == 8
    assert refreshed_job is not None
    assert refreshed_job.status == "completed"
    assert db_session.query(Entity).filter(Entity.document_id == document.id).count() >= 8


def test_worker_processes_multiple_extraction_batches_and_persists_batch_metadata(db_session, monkeypatch):
    _set_entity_extraction_mode(monkeypatch, "ollama")
    _set_entity_extraction_batch_settings(monkeypatch, batch_size=4, max_parallel_batches=2)
    user, space, document = _seed_user_space_document(db_session)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="extraction",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.flush()
    _seed_document_chunks(db_session, document, chunk_count=6)

    queue = InMemoryDocumentProcessingQueue()
    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=space.id,
            uploaded_by=user.id,
            requested_stage="extraction",
            attempt=1,
        )
    )
    extractor = CountingEntityExtractionService()

    assert (
        drain_document_jobs(
            queue=queue,
            storage=InMemoryDocumentStorage(),
            embedding_service=DeterministicEmbeddingService(),
            entity_extraction_service=extractor,
        )
        == 1
    )

    entities = (
        db_session.query(Entity)
        .filter(Entity.document_id == document.id)
        .order_by(Entity.chunk_id.asc(), Entity.normalized_name.asc())
        .all()
    )
    assert extractor.call_count == 2
    assert entities
    assert {entity.extraction_metadata["batch_size"] for entity in entities} == {2, 4}
    assert {entity.extraction_metadata["extraction_mode"] for entity in entities} == {"ollama"}
    assert {entity.extraction_metadata["chunk_index"] for entity in entities} == set(range(6))


def test_worker_maps_out_of_order_batch_results_back_to_chunk_indexes(db_session, monkeypatch):
    _set_entity_extraction_mode(monkeypatch, "ollama")
    _set_entity_extraction_batch_settings(monkeypatch, batch_size=4, max_parallel_batches=2)
    user, space, document = _seed_user_space_document(db_session)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="extraction",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.flush()
    _seed_document_chunks(db_session, document, chunk_count=6)

    queue = InMemoryDocumentProcessingQueue()
    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=space.id,
            uploaded_by=user.id,
            requested_stage="extraction",
            attempt=1,
        )
    )

    assert (
        drain_document_jobs(
            queue=queue,
            storage=InMemoryDocumentStorage(),
            embedding_service=DeterministicEmbeddingService(),
            entity_extraction_service=ReverseBatchEntityExtractionService(),
        )
        == 1
    )

    chunk_id_by_index = {
        chunk.chunk_index: chunk.id
        for chunk in db_session.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).all()
    }
    entities = db_session.query(Entity).filter(Entity.document_id == document.id).all()
    assert entities
    for entity in entities:
        chunk_index = entity.extraction_metadata["chunk_index"]
        assert entity.chunk_id == chunk_id_by_index[chunk_index]


def test_worker_batch_size_one_behaves_like_single_chunk_calls(db_session, monkeypatch):
    _set_entity_extraction_mode(monkeypatch, "ollama")
    _set_entity_extraction_batch_settings(monkeypatch, batch_size=1, max_parallel_batches=1)
    user, space, document = _seed_user_space_document(db_session)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="extraction",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.flush()
    _seed_document_chunks(db_session, document, chunk_count=3)

    queue = InMemoryDocumentProcessingQueue()
    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=space.id,
            uploaded_by=user.id,
            requested_stage="extraction",
            attempt=1,
        )
    )
    extractor = CountingEntityExtractionService()

    assert (
        drain_document_jobs(
            queue=queue,
            storage=InMemoryDocumentStorage(),
            embedding_service=DeterministicEmbeddingService(),
            entity_extraction_service=extractor,
        )
        == 1
    )

    entities = db_session.query(Entity).filter(Entity.document_id == document.id).all()
    assert extractor.call_count == 3
    assert entities
    assert {entity.extraction_metadata["batch_size"] for entity in entities} == {1}


def test_worker_graph_stage_persists_entities_vectors_and_edges(db_session):
    user, space, document = _seed_user_space_document(db_session)
    job = DocumentProcessingJob(
        document_id=document.id,
        space_id=space.id,
        uploaded_by=user.id,
        requested_stage="parsing",
        status="queued",
        attempt=1,
    )
    db_session.add(job)
    db_session.commit()

    storage = InMemoryDocumentStorage()
    storage.store_original_file(document.storage_key, b"Project Atlas works with Ragdoll")
    queue = InMemoryDocumentProcessingQueue()
    queue.enqueue(
        ProcessingJobPayload(
            job_id=job.id,
            document_id=document.id,
            space_id=space.id,
            uploaded_by=user.id,
            requested_stage="parsing",
            attempt=1,
        )
    )

    assert (
        drain_document_jobs(
            queue=queue,
            storage=storage,
            embedding_service=DeterministicEmbeddingService(),
            entity_extraction_service=DeterministicEntityExtractionService(),
        )
        == 1
    )

    assert db_session.query(DocumentChunkVector).filter(DocumentChunkVector.document_id == document.id).count() >= 1
    assert db_session.query(Entity).filter(Entity.document_id == document.id).count() >= 1
    assert db_session.query(GraphEdge).filter(GraphEdge.document_id == document.id).count() >= 1
