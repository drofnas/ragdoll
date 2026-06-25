from pathlib import Path
import sys

import pytest
from fastapi.testclient import TestClient


SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from ragdoll.core import config as config_module
from ragdoll.main import create_app
from ragdoll.platform.db import engine as engine_module
from ragdoll.platform.db import models  # noqa: F401
from ragdoll.platform.db import session as session_module
from ragdoll.platform.db.models_base import Base
from ragdoll.platform.graph import service as graph_service_module
from ragdoll.platform.llm import chat as llm_chat_module
from ragdoll.platform.llm import service as llm_service_module
from ragdoll.platform.queues import service as queue_service_module
from ragdoll.platform.storage import service as storage_service_module
from ragdoll.platform.vector import service as vector_service_module


def reset_runtime_caches() -> None:
    config_module.get_settings.cache_clear()
    engine_module.get_engine.cache_clear()
    session_module.get_session_factory.cache_clear()
    storage_service_module.get_document_storage.cache_clear()
    vector_service_module.get_vector_cleanup_service.cache_clear()
    graph_service_module.get_graph_cleanup_service.cache_clear()
    llm_chat_module.get_chat_completion_service.cache_clear()
    llm_service_module.get_embedding_generation_service.cache_clear()
    llm_service_module.get_entity_extraction_service.cache_clear()
    queue_service_module.get_document_processing_queue.cache_clear()


@pytest.fixture
def configured_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    db_path = tmp_path / "phase2a.sqlite3"

    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    monkeypatch.setenv("SUPABASE_DB_URL", "")
    monkeypatch.setenv("SUPABASE_TEST_DB_URL", "")
    monkeypatch.setenv("RAGDOLL_USE_TEST_DB", "0")
    monkeypatch.setenv("SECRET_KEY", "phase2a-test-secret")
    monkeypatch.setenv("OLLAMA_BASE_URL", "")
    monkeypatch.setenv("OLLAMA_WORKER_BASE_URL", "")

    reset_runtime_caches()
    engine = engine_module.get_engine()
    Base.metadata.create_all(engine)

    try:
        yield db_path
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
        reset_runtime_caches()


@pytest.fixture
def db_session(configured_database):
    session = session_module.get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def api_client(configured_database):
    with TestClient(create_app()) as client:
        yield client
