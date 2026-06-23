from __future__ import annotations

from io import BytesIO
from urllib.parse import urlencode
from uuid import UUID, uuid4

import pytest

from ragdoll.api import dependencies as dependency_module
from ragdoll.core.instance_policy import InstanceLimits
from ragdoll.modules.ingestion.domain import policies as ingestion_policies
from ragdoll.platform.db.models import (
    CanonicalEntity,
    Document,
    DocumentChunk,
    DocumentChunkVector,
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
from ragdoll.workers.document_pipeline import drain_document_jobs


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
    assert statuses[0]["processing_status"]["overall"] == "completed"


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
    storage, queue, _, _, embedding_service, entity_extraction_service = ingestion_runtime
    token = register_and_login(api_client, email="owner@example.com")

    upload = api_client.post(
        "/api/v1/ingestion/uploads",
        headers=auth_headers(token),
        files={"file": ("notes.md", BytesIO(b"# Title\n\nA clean room migration plan."), "text/markdown")},
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
    assert detail.json()["preview_text"].startswith("# Title")
    assert detail.json()["chunk_count"] >= 1

    document = db_session.get(Document, UUID(document_id))
    assert document is not None
    assert db_session.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).count() >= 1
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
    assert response.json()["processing_status"]["parsing"] == "pending"
    assert len(queue.queued_job_ids()) == 1
    assert document_id in vector_cleanup.cleaned_document_ids
    assert document_id in graph_cleanup.cleaned_document_ids
    assert f"derived/{document_id}" not in storage.derived_prefixes

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
    refreshed = db_session.get(Document, document_id)
    assert refreshed is not None
    assert refreshed.processing_status["overall"] == "completed"
    assert refreshed.original_text_content == "updated text content for reprocess"
    assert db_session.query(DocumentChunkVector).filter(DocumentChunkVector.document_id == document_id).count() >= 1
    assert db_session.query(GraphEdge).filter(GraphEdge.document_id == document_id).count() >= 0


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
