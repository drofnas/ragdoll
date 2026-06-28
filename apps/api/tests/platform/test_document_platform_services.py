from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine, inspect

from ragdoll.core.config import Settings
from ragdoll.core.exceptions import ConfigurationError, StorageUnavailableError
from ragdoll.platform.db import models  # noqa: F401
from ragdoll.platform.db.models_base import Base
from ragdoll.platform.graph import InMemoryGraphCleanupService
from ragdoll.platform.storage import InMemoryDocumentStorage, SupabaseDocumentStorage, UnconfiguredDocumentStorage
from ragdoll.platform.vector import InMemoryVectorCleanupService


def test_in_memory_document_storage_round_trip_and_missing_object():
    storage = InMemoryDocumentStorage()

    storage.store_original_file("documents/test.txt", b"hello", content_type="text/plain")

    assert storage.download_original_file("documents/test.txt") == b"hello"
    assert storage.delete_original_file("documents/test.txt") is True
    assert storage.delete_original_file("documents/test.txt") is False

    with pytest.raises(FileNotFoundError):
        storage.download_original_file("documents/test.txt")


def test_unconfigured_document_storage_raises_configuration_error():
    storage = UnconfiguredDocumentStorage()

    with pytest.raises(ConfigurationError):
        storage.download_original_file("documents/missing.txt")


def _supabase_storage() -> SupabaseDocumentStorage:
    return SupabaseDocumentStorage(
        Settings(
            supabase_url="http://kong:8000",
            supabase_service_role_key="test-service-role",
            supabase_storage_bucket="documents",
        )
    )


def test_supabase_document_storage_upload_maps_http_status_errors(monkeypatch: pytest.MonkeyPatch):
    storage = _supabase_storage()
    request = httpx.Request("POST", "http://kong:8000/storage/v1/object/documents/documents/test.txt")
    response = httpx.Response(500, request=request, text='{"error":"boom"}')

    def fake_post(*args, **kwargs):
        del args, kwargs
        raise httpx.HTTPStatusError("upload failed", request=request, response=response)

    monkeypatch.setattr(httpx, "post", fake_post)

    with pytest.raises(StorageUnavailableError) as exc_info:
        storage.store_original_file("documents/test.txt", b"hello", content_type="text/plain")

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "storage_unavailable"


def test_supabase_document_storage_download_distinguishes_missing_vs_backend_failure(monkeypatch: pytest.MonkeyPatch):
    storage = _supabase_storage()
    missing_request = httpx.Request("GET", "http://kong:8000/storage/v1/object/documents/documents/missing.txt")
    failing_request = httpx.Request("GET", "http://kong:8000/storage/v1/object/documents/documents/failing.txt")
    responses = iter(
        [
            httpx.Response(404, request=missing_request),
            httpx.Response(500, request=failing_request, text='{"error":"boom"}'),
        ]
    )

    def fake_get(*args, **kwargs):
        del args, kwargs
        return next(responses)

    monkeypatch.setattr(httpx, "get", fake_get)

    with pytest.raises(FileNotFoundError):
        storage.download_original_file("documents/missing.txt")

    with pytest.raises(StorageUnavailableError):
        storage.download_original_file("documents/failing.txt")


def test_supabase_document_storage_delete_maps_transport_errors(monkeypatch: pytest.MonkeyPatch):
    storage = _supabase_storage()
    request = httpx.Request("DELETE", "http://kong:8000/storage/v1/object/documents/documents/test.txt")

    def fake_delete(*args, **kwargs):
        del args, kwargs
        raise httpx.ConnectError("connection refused", request=request)

    monkeypatch.setattr(httpx, "delete", fake_delete)

    with pytest.raises(StorageUnavailableError):
        storage.delete_original_file("documents/test.txt")


def test_vector_cleanup_is_idempotent():
    service = InMemoryVectorCleanupService()
    document_id = uuid4()

    assert service.cleanup_document(document_id) is True
    assert service.cleanup_document(document_id) is False


def test_graph_cleanup_is_idempotent():
    service = InMemoryGraphCleanupService()
    document_id = uuid4()

    assert service.cleanup_document(document_id) is True
    assert service.cleanup_document(document_id) is False


def test_sqlalchemy_metadata_creates_document_usage_and_ingestion_tables(tmp_path):
    db_path = tmp_path / "phase3a.sqlite3"
    engine = create_engine(f"sqlite+pysqlite:///{db_path}")
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    assert {
        "canonical_entities",
        "documents",
        "document_chunks",
        "document_chunk_vectors",
        "document_processing_jobs",
        "entities",
        "graph_edges",
        "graph_nodes",
        "usage_events",
        "user_usage_snapshots",
    }.issubset(set(inspector.get_table_names()))
    assert "ix_documents_active_space_uploaded_at" in {index["name"] for index in inspector.get_indexes("documents")}
    Base.metadata.drop_all(engine)
    engine.dispose()
