from __future__ import annotations

import httpx
import pytest

from ragdoll.core.config import Settings
from ragdoll.platform.llm.service import OllamaEmbeddingService, OllamaEntityExtractionService


class TimeoutClient:
    def __init__(self, *, timeout=None):
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url: str, json: dict):
        request = httpx.Request("POST", url, json=json)
        raise httpx.ReadTimeout("timed out", request=request)


class JsonResponseStub:
    def __init__(self, payload):
        self._payload = payload
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class JsonClient:
    def __init__(self, payload, *, timeout=None):
        self.payload = payload
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, url: str, json: dict):
        del url, json
        return JsonResponseStub(self.payload)


def test_ollama_embedding_service_uses_configured_timeout_and_raises_clear_message(monkeypatch):
    settings = Settings(
        ollama_worker_base_url="http://ollama.local:11434",
        ollama_embedding_model="nomic-embed-text",
        ollama_worker_timeout_seconds=45,
        _env_file=None,
    )
    captured: dict[str, object] = {}

    def fake_client(*, timeout=None):
        captured["timeout"] = timeout
        return TimeoutClient(timeout=timeout)

    monkeypatch.setattr(httpx, "Client", fake_client)

    service = OllamaEmbeddingService(settings)

    with pytest.raises(TimeoutError, match="Ollama embedding generation timed out after 45.0 seconds."):
        service.generate_embeddings(["hello"])

    assert isinstance(captured["timeout"], httpx.Timeout)
    assert captured["timeout"].read == 45.0


def test_ollama_entity_extraction_service_raises_clear_timeout_message(monkeypatch):
    settings = Settings(
        ollama_worker_base_url="http://ollama.local:11434",
        ollama_worker_model="qwen3.5:0.8b",
        ollama_worker_timeout_seconds=90,
        _env_file=None,
    )

    monkeypatch.setattr(httpx, "Client", lambda *, timeout=None: TimeoutClient(timeout=timeout))

    service = OllamaEntityExtractionService(settings)

    with pytest.raises(TimeoutError, match="Ollama entity extraction timed out after 90.0 seconds."):
        service.extract_entities("Project Atlas works with Ragdoll")


def test_ollama_entity_extraction_service_falls_back_when_model_returns_empty_json_body(monkeypatch):
    settings = Settings(
        ollama_worker_base_url="http://ollama.local:11434",
        ollama_worker_model="qwen3.5:0.8b",
        _env_file=None,
    )

    monkeypatch.setattr(httpx, "Client", lambda *, timeout=None: JsonClient({"response": ""}, timeout=timeout))

    service = OllamaEntityExtractionService(settings)
    entities = service.extract_entities("Project Atlas works with Ragdoll")

    assert [entity.surface_text for entity in entities] == ["Project Atlas", "Ragdoll"]


def test_ollama_entity_extraction_service_falls_back_when_model_returns_unexpected_schema(monkeypatch):
    settings = Settings(
        ollama_worker_base_url="http://ollama.local:11434",
        ollama_worker_model="qwen3.5:0.8b",
        _env_file=None,
    )

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda *, timeout=None: JsonClient({"response": '{"items":[{"name":"Project Atlas"}]}'}, timeout=timeout),
    )

    service = OllamaEntityExtractionService(settings)
    entities = service.extract_entities("Project Atlas works with Ragdoll")

    assert [entity.surface_text for entity in entities] == ["Project Atlas", "Ragdoll"]
