from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import httpx

from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import ConfigurationError
from ragdoll.platform.llm.service import _ollama_timeout


@dataclass(frozen=True)
class ChatCompletionMessage:
    role: str
    content: str


class ChatCompletionService(Protocol):
    def generate(self, messages: list[ChatCompletionMessage]) -> str: ...


class DeterministicChatCompletionService:
    """Test double that keeps chat synthesis deterministic without Ollama."""

    def generate(self, messages: list[ChatCompletionMessage]) -> str:
        user_message = next((message.content for message in reversed(messages) if message.role == "user"), "")
        evidence_lines = [line.strip() for line in user_message.splitlines() if line.strip().startswith("[E")]
        if not evidence_lines:
            return "No scoped evidence was found."
        return "Based on the available evidence:\n" + "\n".join(f"- {line}" for line in evidence_lines[:4])


class OllamaChatCompletionService:
    def __init__(self, settings: Settings) -> None:
        self._base_url = (settings.ollama_base_url or "").rstrip("/")
        self._model = settings.ollama_model.strip()
        self._timeout = _ollama_timeout(settings)

    def generate(self, messages: list[ChatCompletionMessage]) -> str:
        if not self._base_url or not self._model:
            raise ConfigurationError("Ollama chat configuration is incomplete.")
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/api/chat",
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": message.role, "content": message.content}
                            for message in messages
                        ],
                        "stream": False,
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"Ollama chat generation timed out after {self._timeout.read} seconds.") from exc
        except httpx.HTTPError as exc:
            raise ConfigurationError("Ollama chat generation request failed.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise ConfigurationError("Ollama chat response was not valid JSON.") from exc

        message = payload.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            answer = message["content"].strip()
            if answer:
                return answer
        response_text = payload.get("response")
        if isinstance(response_text, str) and response_text.strip():
            return response_text.strip()
        raise ConfigurationError("Ollama chat response did not include answer content.")


@lru_cache(maxsize=1)
def get_chat_completion_service() -> ChatCompletionService:
    settings = get_settings()
    if settings.e2e_shared_backends or settings.e2e_memory_backends:
        return DeterministicChatCompletionService()
    return OllamaChatCompletionService(settings)
