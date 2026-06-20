from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from ragdoll.core.exceptions import ConfigurationError
from ragdoll.platform.graph import InMemoryGraphCleanupService
from ragdoll.platform.storage import InMemoryDocumentStorage, UnconfiguredDocumentStorage
from ragdoll.platform.vector import InMemoryVectorCleanupService

from tests.conftest import reset_runtime_caches


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


def test_alembic_upgrade_head_creates_document_and_usage_tables(monkeypatch, tmp_path):
    db_path = tmp_path / "phase3a.sqlite3"
    repo_root = Path(__file__).resolve().parents[4]
    alembic_ini = repo_root / "apps" / "api" / "alembic.ini"
    migration_path = repo_root / "apps" / "api" / "src" / "ragdoll" / "platform" / "db" / "migrations"

    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    monkeypatch.setenv("SUPABASE_DB_URL", "")
    monkeypatch.setenv("SUPABASE_TEST_DB_URL", "")
    monkeypatch.setenv("RAGDOLL_USE_TEST_DB", "0")
    reset_runtime_caches()

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(migration_path))
    command.upgrade(config, "head")

    inspector = inspect(create_engine(f"sqlite+pysqlite:///{db_path}"))
    assert {"documents", "usage_events", "user_usage_snapshots"}.issubset(set(inspector.get_table_names()))
    assert "ix_documents_active_space_uploaded_at" in {index["name"] for index in inspector.get_indexes("documents")}

    reset_runtime_caches()
