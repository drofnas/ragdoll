from __future__ import annotations

from datetime import timedelta
from io import BytesIO
from urllib.parse import urlencode
from uuid import UUID, uuid4

import pytest

from ragdoll.api import dependencies as dependency_module
from ragdoll.core.exceptions import StorageUnavailableError
from ragdoll.core.instance_policy import InstanceLimits
from ragdoll.modules.ingestion.domain import policies as ingestion_policies
from ragdoll.platform.db.models import (
    CanonicalEntity,
    Document,
    DocumentChunk,
    DocumentChunkVector,
    DocumentProcessingJob,
    Entity,
    GraphEdge,
    GraphNode,
    Space,
    User,
)
from ragdoll.platform.graph import InMemoryGraphCleanupService
from ragdoll.platform.llm import DeterministicEmbeddingService, DeterministicEntityExtractionService
from ragdoll.platform.queues import InMemoryDocumentProcessingQueue
from ragdoll.platform.storage import InMemoryDocumentStorage
from ragdoll.platform.vector import InMemoryVectorCleanupService
from ragdoll.modules.ingestion.application.service import process_job_payload
from ragdoll.platform.queues.service import utc_now
from ragdoll.workers.document_pipeline import drain_document_jobs


class FailingUploadStorage:
    def store_original_file(self, storage_key: str, content: bytes, *, content_type: str | None = None) -> None:
        del storage_key, content, content_type
        raise StorageUnavailableError("Document storage is temporarily unavailable while attempting to store the uploaded document file.")

    def download_original_file(self, storage_key: str) -> bytes:
        del storage_key
        raise NotImplementedError

    def delete_original_file(self, storage_key: str) -> bool:
        del storage_key
        raise NotImplementedError

    def delete_derived_artifacts(self, document_id, *, storage_prefix: str | None = None) -> bool:
        del document_id, storage_prefix
        raise NotImplementedError


def register_and_login(api_client, *, email: str = "user@example.com", password: str = "testpass123") -> str:
    register = api_client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": "Test User"},
    )
    assert register.status_code == 201, register.text
    login = api_client.post(
        "/api/v1/auth/login",
        content=urlencode({"username": email, "password": password}),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def default_space(db_session, user: User) -> Space:
    return (
        db_session.query(Space)
        .filter(Space.owner_user_id == user.id, Space.is_default.is_(True))
        .one()
    )


def seed_stale_processing_state(
    db_session,
    *,
    document_id: UUID,
    stage: str,
    age: timedelta,
    started_at_missing: bool = False,
) -> DocumentProcessingJob:
    document = db_session.get(Document, document_id)
    assert document is not None
    job = (
        db_session.query(DocumentProcessingJob)
        .filter(DocumentProcessingJob.document_id == document_id)
        .filter(DocumentProcessingJob.status == "processing")
        .order_by(DocumentProcessingJob.queued_at.asc())
        .first()
    )
    if job is None:
        job = (
            db_session.query(DocumentProcessingJob)
            .filter(DocumentProcessingJob.document_id == document_id)
            .order_by(DocumentProcessingJob.queued_at.desc())
            .first()
        )
    assert job is not None

    stale_at = utc_now() - age
    document.processing_status = {
        "overall": "processing",
        "upload": "completed",
        "parsing": "completed" if stage != "parsing" else "processing",
        "vector": "completed" if stage not in {"parsing", "vector"} else ("processing" if stage == "vector" else "pending"),
        "extraction": (
            "completed" if stage == "graph" else ("processing" if stage == "extraction" else "pending")
        ),
        "graph": "processing" if stage == "graph" else "pending",
        "detail": None,
    }
    job.status = "processing"
    job.started_at = None if started_at_missing else stale_at
    job.queued_at = stale_at
    job.completed_at = None
    job.visible_error_detail = None
    db_session.commit()
    return job


@pytest.fixture
def ingestion_runtime(api_client):
    storage = InMemoryDocumentStorage()
    queue = InMemoryDocumentProcessingQueue()
    vector_cleanup = InMemoryVectorCleanupService()
    graph_cleanup = InMemoryGraphCleanupService()
    embedding_service = DeterministicEmbeddingService()
    entity_extraction_service = DeterministicEntityExtractionService()
    api_client.app.dependency_overrides[dependency_module.get_document_storage_service] = lambda: storage
    api_client.app.dependency_overrides[dependency_module.get_document_processing_queue_service] = lambda: queue
    api_client.app.dependency_overrides[dependency_module.get_vector_cleanup] = lambda: vector_cleanup
    api_client.app.dependency_overrides[dependency_module.get_graph_cleanup] = lambda: graph_cleanup
    try:
        yield storage, queue, vector_cleanup, graph_cleanup, embedding_service, entity_extraction_service
    finally:
        api_client.app.dependency_overrides.clear()


def test_ingestion_routes_require_authentication(api_client):
    document_id = uuid4()
    responses = [
        api_client.post("/api/v1/ingestion/uploads"),
        api_client.get(f"/api/v1/ingestion/documents/{document_id}/status"),
        api_client.post("/api/v1/ingestion/documents/status/batch", json={"document_ids": []}),
        api_client.post(f"/api/v1/ingestion/documents/{document_id}/reprocess"),
        api_client.post(f"/api/v1/ingestion/documents/{document_id}/retry/parsing"),
        api_client.post(f"/api/v1/ingestion/documents/{document_id}/retry/vector"),
        api_client.post(f"/api/v1/ingestion/documents/{document_id}/retry/extraction"),
        api_client.post(f"/api/v1/ingestion/documents/{document_id}/retry/graph"),
    ]
    assert all(response.status_code == 401 for response in responses)


def test_chunk_text_with_lines_tracks_source_line_numbers():
    chunks = ingestion_policies.chunk_text_with_lines(
        "Title\n\nFirst paragraph starts here.\nSecond paragraph continues here.",
        chunk_size=3,
        overlap=0,
    )

    assert [(chunk.text, chunk.start_line) for chunk in chunks] == [
        ("Title First paragraph", 1),
        ("starts here. Second", 3),
        ("paragraph continues here.", 4),
    ]


def test_upload_uses_default_space_and_enqueues_job(api_client, db_session, ingestion_runtime):
    _, queue, _, _, _, _ = ingestion_runtime
    token = register_and_login(api_client, email="owner@example.com")
    owner = db_session.query(User).filter(User.email == "owner@example.com").one()
    owner_default = default_space(db_session, owner)

    response = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("architecture notes.txt", BytesIO(b"hello world"), "text/plain")},
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["filename"] == "architecture_notes.txt"
    assert payload["processing_status"]["parsing"] == "pending"
    assert payload["processing_status"]["vector"] == "pending"
    assert len(queue.queued_job_ids()) == 1

    document = db_session.get(Document, UUID(payload["document_id"]))
    assert document is not None
    assert document.space_id == owner_default.id
    assert document.original_filename == "architecture_notes.txt"


def test_upload_rejects_invalid_file_type(api_client, ingestion_runtime):
    ingestion_runtime
    token = register_and_login(api_client)
    response = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("script.exe", BytesIO(b"whoops"), "application/octet-stream")},
    )
    assert response.status_code == 400, response.text
    assert response.json()["code"] == "unsupported_file_type"


def test_upload_rejects_invalid_filename(api_client, ingestion_runtime):
    ingestion_runtime
    token = register_and_login(api_client)
    response = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("....pdf", BytesIO(b"fake"), "application/pdf")},
    )
    assert response.status_code == 400, response.text
    assert response.json()["code"] == "invalid_filename"


def test_upload_rejects_other_users_space(api_client, db_session, ingestion_runtime):
    ingestion_runtime
    token_a = register_and_login(api_client, email="owner-a@example.com")
    token_b = register_and_login(api_client, email="owner-b@example.com")
    owner_a = db_session.query(User).filter(User.email == "owner-a@example.com").one()
    space_id = default_space(db_session, owner_a).id

    response = api_client.post(
        f"/api/v1/ingestion/uploads?space_id={space_id}",
        headers=auth_headers(token_b),
        files={"file": ("doc.txt", BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 404, response.text
    assert response.json()["code"] == "space_not_found"


def test_upload_rejects_oversized_file(api_client, ingestion_runtime):
    ingestion_runtime
    token = register_and_login(api_client)
    oversized = b"x" * 5
    original_resolver = ingestion_policies.resolve_instance_limits
    ingestion_policies.resolve_instance_limits = lambda: InstanceLimits(
        documents=None,
        max_file_size_bytes=4,
        chunks=None,
        storage_bytes=None,
        tokens_5h=None,
        tokens_week=None,
        retrieval_chunks=20,
        output_tokens=2400,
        per_document_chunks=2000,
    )
    response = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("big.txt", BytesIO(oversized), "text/plain")},
    )
    try:
        assert response.status_code == 413, response.text
        assert response.json()["code"] == "upload_file_too_large"
    finally:
        ingestion_policies.resolve_instance_limits = original_resolver


def test_upload_returns_service_unavailable_when_storage_write_fails(api_client, db_session):
    queue = InMemoryDocumentProcessingQueue()
    vector_cleanup = InMemoryVectorCleanupService()
    graph_cleanup = InMemoryGraphCleanupService()
    api_client.app.dependency_overrides[dependency_module.get_document_storage_service] = lambda: FailingUploadStorage()
    api_client.app.dependency_overrides[dependency_module.get_document_processing_queue_service] = lambda: queue
    api_client.app.dependency_overrides[dependency_module.get_vector_cleanup] = lambda: vector_cleanup
    api_client.app.dependency_overrides[dependency_module.get_graph_cleanup] = lambda: graph_cleanup
    try:
        token = register_and_login(api_client, email="storage-failure@example.com")
        response = api_client.post(
            "/api/v1/ingestion/uploads",
            headers=auth_headers(token),
            files={"file": ("broken.txt", BytesIO(b"cannot store"), "text/plain")},
        )

        assert response.status_code == 503, response.text
        assert response.json()["code"] == "storage_unavailable"
        assert db_session.query(Document).count() == 0
    finally:
        api_client.app.dependency_overrides.clear()


def test_batch_status_dedupes_and_filters_visibility(api_client, db_session, ingestion_runtime):
    storage, queue, _, _, embedding_service, entity_extraction_service = ingestion_runtime
    token_a = register_and_login(api_client, email="owner-a@example.com")
    token_b = register_and_login(api_client, email="owner-b@example.com")

    upload_a = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token_a),
        files={"file": ("alpha.txt", BytesIO(b"alpha text"), "text/plain")},
    )
    upload_b = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token_b),
        files={"file": ("beta.txt", BytesIO(b"beta text"), "text/plain")},
    )
    assert upload_a.status_code == 201, upload_a.text
    assert upload_b.status_code == 201, upload_b.text
    drain_document_jobs(
        queue=queue,
        storage=storage,
        embedding_service=embedding_service,
        entity_extraction_service=entity_extraction_service,
    )

    visible_id = upload_a.json()["document_id"]
    hidden_id = upload_b.json()["document_id"]
    response = api_client.post(
        "/api/v1/ingestion/documents/status/batch",
        headers=auth_headers(token_a),
        json={"document_ids": [visible_id, visible_id, hidden_id]},
    )
    assert response.status_code == 200, response.text
    statuses = response.json()["statuses"]
    assert len(statuses) == 1
    assert statuses[0]["document_id"] == visible_id
    assert statuses[0]["active_job"] is None
    assert statuses[0]["queued_job_count"] == 0
    assert statuses[0]["has_queued_reprocess"] is False
    assert statuses[0]["processing_status"]["overall"] == "completed"


def test_document_status_reconciles_stale_processing_jobs_without_started_at(api_client, db_session, ingestion_runtime):
    _, queue, _, _, _, _ = ingestion_runtime
    token = register_and_login(api_client, email="stale-single@example.com")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("stale.txt", BytesIO(b"stale"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document_id = UUID(upload.json()["document_id"])

    active_payload = queue.claim_next_job()
    assert active_payload is not None
    stale_job = seed_stale_processing_state(
        db_session,
        document_id=document_id,
        stage="parsing",
        age=timedelta(minutes=11),
        started_at_missing=True,
    )

    response = api_client.get(
        f"/api/v1/ingestion/documents/{document_id}/status",
        headers=auth_headers(token),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["active_job"] is None
    assert payload["queued_job_count"] == 0
    assert payload["processing_status"]["overall"] == "failed"
    assert payload["processing_status"]["parsing"] == "failed"
    assert "timed out" in payload["processing_status"]["detail"].lower()

    db_session.expire_all()
    refreshed_job = db_session.get(DocumentProcessingJob, stale_job.id)
    refreshed_document = db_session.get(Document, document_id)
    assert refreshed_job is not None
    assert refreshed_document is not None
    assert refreshed_job.status == "failed"
    assert refreshed_job.completed_at is not None
    assert refreshed_job.visible_error_detail is not None
    assert "timed out" in refreshed_job.visible_error_detail.lower()
    assert refreshed_document.processing_status["overall"] == "failed"
    assert refreshed_document.processing_status["detail"] == refreshed_job.visible_error_detail[:500]


def test_batch_status_reconciles_stale_processing_jobs_for_visible_rows(api_client, db_session, ingestion_runtime):
    _, queue, _, _, _, _ = ingestion_runtime
    token = register_and_login(api_client, email="stale-batch@example.com")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("stale-extract.txt", BytesIO(b"stale"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document_id = UUID(upload.json()["document_id"])

    active_payload = queue.claim_next_job()
    assert active_payload is not None
    stale_job = seed_stale_processing_state(
        db_session,
        document_id=document_id,
        stage="extraction",
        age=timedelta(hours=2),
    )

    response = api_client.post(
        "/api/v1/ingestion/documents/status/batch",
        headers=auth_headers(token),
        json={"document_ids": [str(document_id)]},
    )
    assert response.status_code == 200, response.text
    statuses = response.json()["statuses"]
    assert len(statuses) == 1
    assert statuses[0]["document_id"] == str(document_id)
    assert statuses[0]["active_job"] is None
    assert statuses[0]["processing_status"]["overall"] == "failed"
    assert statuses[0]["processing_status"]["extraction"] == "failed"

    db_session.expire_all()
    refreshed_job = db_session.get(DocumentProcessingJob, stale_job.id)
    assert refreshed_job is not None
    assert refreshed_job.status == "failed"


def test_batch_status_rejects_more_than_100_ids(api_client, ingestion_runtime):
    ingestion_runtime
    token = register_and_login(api_client)
    response = api_client.post(
        "/api/v1/ingestion/documents/status/batch",
        headers=auth_headers(token),
        json={"document_ids": [str(uuid4()) for _ in range(101)]},
    )
    assert response.status_code == 422, response.text


def test_worker_processing_updates_document_reads(api_client, db_session, ingestion_runtime):
    storage, queue, vector_cleanup, graph_cleanup, embedding_service, entity_extraction_service = ingestion_runtime
    token = register_and_login(api_client, email="owner@example.com")
    line_one = " ".join(["Atlas", *(["a"] * 149)])
    line_three = " ".join(["b"] * 300)
    line_four = " ".join(["c"] * 60)
    content = f"{line_one}\n\n{line_three}\n{line_four}".encode("utf-8")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("notes.md", BytesIO(content), "text/markdown")},
    )
    assert upload.status_code == 201, upload.text
    document_id = upload.json()["document_id"]

    assert (
        drain_document_jobs(
            queue=queue,
            storage=storage,
            embedding_service=embedding_service,
            entity_extraction_service=entity_extraction_service,
        )
        == 1
    )

    status = api_client.get(
        f"/api/v1/ingestion/documents/{document_id}/status",
        headers=auth_headers(token),
    )
    assert status.status_code == 200, status.text
    status_payload = status.json()
    assert status_payload["processing_status"]["overall"] == "completed"
    assert status_payload["processing_status"]["vector"] == "completed"
    assert status_payload["processing_status"]["extraction"] == "completed"
    assert status_payload["processing_status"]["graph"] == "completed"
    assert status_payload["chunk_count"] >= 1
    assert status_payload["indexed_chunk_count"] >= 1

    detail = api_client.get(f"/api/v1/documents/{document_id}", headers=auth_headers(token))
    assert detail.status_code == 200, detail.text
    assert detail.json()["preview_text"].startswith("Atlas")
    assert detail.json()["chunk_count"] >= 2

    document = db_session.get(Document, UUID(document_id))
    assert document is not None
    chunks = (
        db_session.query(DocumentChunk)
        .filter(DocumentChunk.document_id == document.id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )
    assert [chunk.start_line for chunk in chunks] == [1, 4]
    assert db_session.query(DocumentChunkVector).filter(DocumentChunkVector.document_id == document.id).count() >= 1
    assert db_session.query(Entity).filter(Entity.document_id == document.id).count() >= 1
    assert db_session.query(CanonicalEntity).filter(CanonicalEntity.space_id == document.space_id).count() >= 1
    assert db_session.query(GraphNode).count() >= 1


def test_reprocess_clears_existing_chunks_and_enqueues_new_job(api_client, db_session, ingestion_runtime):
    storage, queue, vector_cleanup, graph_cleanup, embedding_service, entity_extraction_service = ingestion_runtime
    token = register_and_login(api_client, email="owner@example.com")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("notes.txt", BytesIO(b"original"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document_id = UUID(upload.json()["document_id"])
    drain_document_jobs(
        queue=queue,
        storage=storage,
        embedding_service=embedding_service,
        entity_extraction_service=entity_extraction_service,
    )

    document = db_session.get(Document, document_id)
    assert document is not None
    storage.derived_prefixes.add(f"derived/{document_id}")
    storage.store_original_file(document.storage_key, b"updated text content for reprocess")

    response = api_client.post(
        f"/api/v1/ingestion/documents/{document_id}/reprocess",
        headers=auth_headers(token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["queued_job_count"] == 1
    assert response.json()["has_queued_reprocess"] is True
    assert len(queue.queued_job_ids()) == 1
    assert document_id not in vector_cleanup.cleaned_document_ids
    assert document_id not in graph_cleanup.cleaned_document_ids
    assert f"derived/{document_id}" in storage.derived_prefixes

    assert (
        drain_document_jobs(
            queue=queue,
            storage=storage,
            embedding_service=embedding_service,
            entity_extraction_service=entity_extraction_service,
            vector_cleanup=vector_cleanup,
            graph_cleanup=graph_cleanup,
        )
        == 1
    )
    db_session.expire_all()
    refreshed = db_session.get(Document, document_id)
    assert refreshed is not None
    assert refreshed.processing_status["overall"] == "completed"
    assert refreshed.original_text_content == "updated text content for reprocess"
    assert document_id in vector_cleanup.cleaned_document_ids
    assert document_id in graph_cleanup.cleaned_document_ids
    assert f"derived/{document_id}" not in storage.derived_prefixes
    assert db_session.query(DocumentChunkVector).filter(DocumentChunkVector.document_id == document_id).count() >= 1
    assert db_session.query(GraphEdge).filter(GraphEdge.document_id == document_id).count() >= 0


def test_reprocess_queues_one_follow_up_behind_an_active_job(api_client, db_session, ingestion_runtime):
    storage, queue, vector_cleanup, graph_cleanup, embedding_service, entity_extraction_service = ingestion_runtime
    token = register_and_login(api_client, email="follow-up@example.com")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("notes.txt", BytesIO(b"original"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document_id = UUID(upload.json()["document_id"])

    active_payload = queue.claim_next_job()
    assert active_payload is not None

    first_reprocess = api_client.post(
        f"/api/v1/ingestion/documents/{document_id}/reprocess",
        headers=auth_headers(token),
    )
    assert first_reprocess.status_code == 200, first_reprocess.text
    first_payload = first_reprocess.json()
    assert first_payload["active_job"]["status"] == "processing"
    assert first_payload["queued_job_count"] == 1
    assert first_payload["has_queued_reprocess"] is True
    assert len(queue.queued_job_ids()) == 1

    second_reprocess = api_client.post(
        f"/api/v1/ingestion/documents/{document_id}/reprocess",
        headers=auth_headers(token),
    )
    assert second_reprocess.status_code == 200, second_reprocess.text
    assert second_reprocess.json()["queued_job_count"] == 1
    assert len(queue.queued_job_ids()) == 1

    document = db_session.get(Document, document_id)
    assert document is not None
    storage.derived_prefixes.add(f"derived/{document_id}")
    storage.store_original_file(document.storage_key, b"updated text content for reprocess")

    process_job_payload(
        active_payload,
        queue=queue,
        storage=storage,
        embedding_service=embedding_service,
        entity_extraction_service=entity_extraction_service,
        vector_cleanup=vector_cleanup,
        graph_cleanup=graph_cleanup,
    )

    assert f"derived/{document_id}" in storage.derived_prefixes

    assert (
        drain_document_jobs(
            queue=queue,
            storage=storage,
            embedding_service=embedding_service,
            entity_extraction_service=entity_extraction_service,
            vector_cleanup=vector_cleanup,
            graph_cleanup=graph_cleanup,
        )
        == 1
    )

    assert document_id in vector_cleanup.cleaned_document_ids
    assert document_id in graph_cleanup.cleaned_document_ids
    assert f"derived/{document_id}" not in storage.derived_prefixes


def test_reprocess_reconciles_stale_processing_before_enqueuing_fresh_job(api_client, db_session, ingestion_runtime):
    _, queue, _, _, _, _ = ingestion_runtime
    token = register_and_login(api_client, email="stale-reprocess@example.com")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("retry.txt", BytesIO(b"retry"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document_id = UUID(upload.json()["document_id"])

    active_payload = queue.claim_next_job()
    assert active_payload is not None
    stale_job = seed_stale_processing_state(
        db_session,
        document_id=document_id,
        stage="extraction",
        age=timedelta(hours=2),
    )

    response = api_client.post(
        f"/api/v1/ingestion/documents/{document_id}/reprocess",
        headers=auth_headers(token),
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["active_job"] is None
    assert payload["queued_job_count"] == 1
    assert payload["has_queued_reprocess"] is True
    assert len(queue.queued_job_ids()) == 1

    db_session.expire_all()
    refreshed_job = db_session.get(DocumentProcessingJob, stale_job.id)
    assert refreshed_job is not None
    assert refreshed_job.status == "failed"


def test_queue_claim_fails_stale_processing_before_claiming_follow_up_job(api_client, db_session, ingestion_runtime):
    _, queue, _, _, _, _ = ingestion_runtime
    token = register_and_login(api_client, email="stale-follow-up@example.com")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("follow-up.txt", BytesIO(b"follow-up"), "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document_id = UUID(upload.json()["document_id"])

    active_payload = queue.claim_next_job()
    assert active_payload is not None

    reprocess = api_client.post(
        f"/api/v1/ingestion/documents/{document_id}/reprocess",
        headers=auth_headers(token),
    )
    assert reprocess.status_code == 200, reprocess.text
    queued_follow_up_id = queue.queued_job_ids()[0]

    stale_job = seed_stale_processing_state(
        db_session,
        document_id=document_id,
        stage="extraction",
        age=timedelta(hours=2),
    )

    next_payload = queue.claim_next_job()
    assert next_payload is not None
    assert next_payload.job_id == queued_follow_up_id

    db_session.expire_all()
    refreshed_stale_job = db_session.get(DocumentProcessingJob, stale_job.id)
    claimed_job = db_session.get(DocumentProcessingJob, queued_follow_up_id)
    assert refreshed_stale_job is not None
    assert claimed_job is not None
    assert refreshed_stale_job.status == "failed"
    assert claimed_job.status == "processing"


@pytest.mark.parametrize(
    ("path_suffix", "expected_status"),
    [
        ("retry/vector", {"parsing": "completed", "vector": "pending", "extraction": "pending", "graph": "pending"}),
        ("retry/extraction", {"parsing": "completed", "vector": "completed", "extraction": "pending", "graph": "pending"}),
        ("retry/graph", {"parsing": "completed", "vector": "completed", "extraction": "completed", "graph": "pending"}),
    ],
)
def test_targeted_retries_reset_only_downstream_stages(
    api_client,
    db_session,
    ingestion_runtime,
    path_suffix,
    expected_status,
):
    storage, queue, _, _, embedding_service, entity_extraction_service = ingestion_runtime
    token = register_and_login(api_client, email=f"{path_suffix.replace('/', '-') }@example.com")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("notes.md", BytesIO(b"# Alpha\n\nProject Atlas meets Ragdoll."), "text/markdown")},
    )
    assert upload.status_code == 201, upload.text
    document_id = UUID(upload.json()["document_id"])
    assert (
        drain_document_jobs(
            queue=queue,
            storage=storage,
            embedding_service=embedding_service,
            entity_extraction_service=entity_extraction_service,
        )
        == 1
    )

    response = api_client.post(
        f"/api/v1/ingestion/documents/{document_id}/{path_suffix}",
        headers=auth_headers(token),
    )
    assert response.status_code == 200, response.text
    payload = response.json()["processing_status"]
    assert payload["overall"] == "pending"
    for key, value in expected_status.items():
        assert payload[key] == value
    assert len(queue.queued_job_ids()) == 1

    refreshed = db_session.get(Document, document_id)
    assert refreshed is not None
    assert refreshed.processing_status["overall"] == "pending"


def test_reprocess_with_identical_content_keeps_projection_counts_stable(api_client, db_session, ingestion_runtime):
    storage, queue, _, _, embedding_service, entity_extraction_service = ingestion_runtime
    token = register_and_login(api_client, email="stable@example.com")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("stable.txt", BytesIO(b"Project Atlas supports Ragdoll."), "text/plain")},
    )
    assert upload.status_code == 201, upload.text
    document_id = UUID(upload.json()["document_id"])
    assert (
        drain_document_jobs(
            queue=queue,
            storage=storage,
            embedding_service=embedding_service,
            entity_extraction_service=entity_extraction_service,
        )
        == 1
    )

    first_chunk_ids = {
        row.id for row in db_session.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    }
    first_vector_count = db_session.query(DocumentChunkVector).filter(DocumentChunkVector.document_id == document_id).count()
    first_entity_count = db_session.query(Entity).filter(Entity.document_id == document_id).count()
    first_edge_count = db_session.query(GraphEdge).filter(GraphEdge.document_id == document_id).count()

    document = db_session.get(Document, document_id)
    assert document is not None
    storage.store_original_file(document.storage_key, b"Project Atlas supports Ragdoll.")

    reprocess = api_client.post(
        f"/api/v1/ingestion/documents/{document_id}/reprocess",
        headers=auth_headers(token),
    )
    assert reprocess.status_code == 200, reprocess.text
    assert (
        drain_document_jobs(
            queue=queue,
            storage=storage,
            embedding_service=embedding_service,
            entity_extraction_service=entity_extraction_service,
        )
        == 1
    )

    second_chunk_ids = {
        row.id for row in db_session.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).all()
    }
    assert second_chunk_ids == first_chunk_ids
    assert db_session.query(DocumentChunkVector).filter(DocumentChunkVector.document_id == document_id).count() == first_vector_count
    assert db_session.query(Entity).filter(Entity.document_id == document_id).count() == first_entity_count
    assert db_session.query(GraphEdge).filter(GraphEdge.document_id == document_id).count() == first_edge_count
