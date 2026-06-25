from __future__ import annotations

import httpx
import pytest

from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import ConfigurationError
from ragdoll.platform.llm.chat import ChatCompletionMessage, OllamaChatCompletionService
from ragdoll.platform.llm.service import (
    DeterministicEntityExtractionService,
    EntityExtractionError,
    OllamaEmbeddingService,
    OllamaEntityExtractionService,
    get_entity_extraction_service,
)


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


def test_ollama_entity_extraction_service_raises_when_model_returns_empty_json_body(monkeypatch):
    settings = Settings(
        ollama_worker_base_url="http://ollama.local:11434",
        ollama_worker_model="qwen3.5:0.8b",
        _env_file=None,
    )

    monkeypatch.setattr(httpx, "Client", lambda *, timeout=None: JsonClient({"response": ""}, timeout=timeout))

    service = OllamaEntityExtractionService(settings)
    with pytest.raises(EntityExtractionError, match="malformed JSON"):
        service.extract_entities("Project Atlas works with Ragdoll")


def test_ollama_entity_extraction_service_raises_when_model_returns_unexpected_schema(monkeypatch):
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
    with pytest.raises(EntityExtractionError, match="unexpected schema"):
        service.extract_entities("Project Atlas works with Ragdoll")


def test_ollama_chat_completion_service_returns_message_content(monkeypatch):
    settings = Settings(
        ollama_base_url="http://ollama.local:11434",
        ollama_model="qwen3.5:0.8b",
        _env_file=None,
    )
    captured: dict[str, object] = {}

    class CapturingClient(JsonClient):
        def post(self, url: str, json: dict):
            captured["url"] = url
            captured["json"] = json
            return JsonResponseStub({"message": {"content": "Synthesized answer [E1]"}})

    monkeypatch.setattr(httpx, "Client", lambda *, timeout=None: CapturingClient({}, timeout=timeout))

    service = OllamaChatCompletionService(settings)
    answer = service.generate([ChatCompletionMessage(role="user", content="Answer this")])

    assert answer == "Synthesized answer [E1]"
    assert captured["url"] == "http://ollama.local:11434/api/chat"
    assert captured["json"]["model"] == "qwen3.5:0.8b"
    assert captured["json"]["stream"] is False


def test_ollama_chat_completion_service_rejects_empty_response(monkeypatch):
    settings = Settings(
        ollama_base_url="http://ollama.local:11434",
        ollama_model="qwen3.5:0.8b",
        _env_file=None,
    )
    monkeypatch.setattr(httpx, "Client", lambda *, timeout=None: JsonClient({"message": {"content": ""}}, timeout=timeout))

    service = OllamaChatCompletionService(settings)
    with pytest.raises(ConfigurationError, match="answer content"):
        service.generate([ChatCompletionMessage(role="user", content="Answer this")])


def test_get_entity_extraction_service_uses_deterministic_mode(monkeypatch):
    monkeypatch.setenv("ENTITY_EXTRACTION_MODE", "deterministic")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://ollama.local:11434")
    get_settings.cache_clear()
    get_entity_extraction_service.cache_clear()
    try:
        assert isinstance(get_entity_extraction_service(), DeterministicEntityExtractionService)
    finally:
        get_settings.cache_clear()
        get_entity_extraction_service.cache_clear()
