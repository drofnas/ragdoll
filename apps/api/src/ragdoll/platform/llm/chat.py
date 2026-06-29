from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Protocol

import httpx

from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import ConfigurationError
from ragdoll.core.logging import get_logger

logger = get_logger("ragdoll.platform.llm.chat")


@dataclass(frozen=True)
class ChatCompletionMessage:
    role: str
    content: str


class ChatCompletionService(Protocol):
    def generate(
        self,
        messages: list[ChatCompletionMessage],
        *,
        format: dict[str, Any] | str | None = None,
    ) -> str: ...


class DeterministicChatCompletionService:
    """Test double that keeps chat synthesis deterministic without Ollama."""

    def generate(
        self,
        messages: list[ChatCompletionMessage],
        *,
        format: dict[str, Any] | str | None = None,
    ) -> str:
        system_message = next((message.content for message in messages if message.role == "system"), "")
        user_message = next((message.content for message in reversed(messages) if message.role == "user"), "")
        is_pinned_fact_detector = "pinned-fact detector" in system_message.lower()
        logger.info(
            "chat_completion_generate service=deterministic request_type=%s message_count=%s user_chars=%s structured_format=%s",
            "pinned_fact_detector" if is_pinned_fact_detector else "chat",
            len(messages),
            len(user_message),
            "schema" if isinstance(format, dict) else format or "none",
        )
        if is_pinned_fact_detector:
            value_kind_match = re.search(r"Requested value kind:\s*(text|json)", user_message)
            value_kind = value_kind_match.group(1) if value_kind_match is not None else "text"
            evidence_lines = [
                line.strip()
                for line in user_message.splitlines()
                if line.strip().startswith("[E") and "text=" in line
            ]
            logger.info(
                "chat_completion_pinned_fact_detector service=deterministic value_kind=%s evidence_line_count=%s",
                value_kind,
                len(evidence_lines),
            )
            if not evidence_lines:
                if value_kind_match is None:
                    return json.dumps(
                        {
                            "status": "insufficient_evidence",
                            "suggested_answers": [],
                            "evidence_ids": [],
                            "message": "No scoped evidence was found."
                        }
                    )
                return json.dumps(
                    {
                        "status": "insufficient_evidence",
                        "value_text": None,
                        "value_json": None,
                        "evidence_ids": [],
                        "message": "No scoped evidence was found."
                    }
                )
            first_line = evidence_lines[0]
            evidence_id_match = re.match(r"\[(E\d+)\]", first_line)
            evidence_id = evidence_id_match.group(1) if evidence_id_match is not None else "E1"
            value_text = first_line.split("text=", 1)[1].strip()
            if value_kind_match is None:
                return json.dumps(
                    {
                        "status": "ready",
                        "suggested_answers": [value_text],
                        "evidence_ids": [evidence_id],
                        "message": "Deterministic shared-backend synthesis."
                    }
                )
            if value_kind == "json":
                return json.dumps(
                    {
                        "status": "ready",
                        "value_text": None,
                        "value_json": {"value": value_text},
                        "evidence_ids": [evidence_id],
                        "message": "Deterministic shared-backend synthesis."
                    }
                )
            return json.dumps(
                {
                    "status": "ready",
                    "value_text": value_text,
                    "value_json": None,
                    "evidence_ids": [evidence_id],
                    "message": "Deterministic shared-backend synthesis."
                }
            )
        evidence_lines = [line.strip() for line in user_message.splitlines() if line.strip().startswith("[E")]
        if not evidence_lines:
            return "No scoped evidence was found."
        return "Based on the available evidence:\n" + "\n".join(f"- {line}" for line in evidence_lines[:4])


class OllamaChatCompletionService:
    def __init__(self, settings: Settings) -> None:
        self._base_url = (settings.ollama_base_url or "").rstrip("/")
        self._model = settings.ollama_model.strip()
        self._timeout = httpx.Timeout(
            connect=10.0,
            read=settings.ollama_chat_timeout_seconds,
            write=settings.ollama_chat_timeout_seconds,
            pool=settings.ollama_chat_timeout_seconds,
        )
        self._max_tokens = settings.ollama_chat_max_tokens
        self._context_window = settings.ollama_chat_context_window
        self._think = settings.ollama_chat_think

    def generate(
        self,
        messages: list[ChatCompletionMessage],
        *,
        format: dict[str, Any] | str | None = None,
    ) -> str:
        if not self._base_url or not self._model:
            raise ConfigurationError("Ollama chat configuration is incomplete.")
        system_message = next((message.content for message in messages if message.role == "system"), "")
        user_message = next((message.content for message in reversed(messages) if message.role == "user"), "")
        is_pinned_fact_detector = "pinned-fact detector" in system_message.lower()
        logger.info(
            "chat_completion_generate service=ollama request_type=%s model=%s message_count=%s user_chars=%s think=%s max_tokens=%s context_window=%s structured_format=%s",
            "pinned_fact_detector" if is_pinned_fact_detector else "chat",
            self._model,
            len(messages),
            len(user_message),
            self._think,
            self._max_tokens,
            self._context_window,
            "schema" if isinstance(format, dict) else format or "none",
        )
        prompt_chars = sum(len(message.content) for message in messages)
        if prompt_chars > self._context_window:
            logger.warning(
                "chat_completion_prompt_chars_exceed_context service=ollama request_type=%s model=%s prompt_chars=%s context_window=%s",
                "pinned_fact_detector" if is_pinned_fact_detector else "chat",
                self._model,
                prompt_chars,
                self._context_window,
            )
        request_payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "stream": False,
            "think": self._think,
            "options": {
                "temperature": 0,
                "num_predict": self._max_tokens,
                "num_ctx": self._context_window,
            },
        }
        if format is not None:
            request_payload["format"] = format
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/api/chat",
                    json=request_payload,
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            logger.warning(
                "chat_completion_timeout service=ollama request_type=%s model=%s timeout_seconds=%s",
                "pinned_fact_detector" if is_pinned_fact_detector else "chat",
                self._model,
                self._timeout.read,
            )
            raise TimeoutError(f"Ollama chat generation timed out after {self._timeout.read} seconds.") from exc
        except httpx.HTTPError as exc:
            logger.warning(
                "chat_completion_http_error service=ollama request_type=%s model=%s error_type=%s error=%s",
                "pinned_fact_detector" if is_pinned_fact_detector else "chat",
                self._model,
                type(exc).__name__,
                exc,
            )
            raise ConfigurationError("Ollama chat generation request failed.") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            logger.warning(
                "chat_completion_invalid_json service=ollama request_type=%s model=%s",
                "pinned_fact_detector" if is_pinned_fact_detector else "chat",
                self._model,
            )
            raise ConfigurationError("Ollama chat response was not valid JSON.") from exc

        message = payload.get("message")
        if isinstance(message, dict) and isinstance(message.get("content"), str):
            answer = message["content"].strip()
            if answer:
                logger.info(
                    "chat_completion_response service=ollama request_type=%s model=%s answer_chars=%s used_field=message.content",
                    "pinned_fact_detector" if is_pinned_fact_detector else "chat",
                    self._model,
                    len(answer),
                )
                return answer
            thinking = message.get("thinking")
            if isinstance(thinking, str) and thinking.strip():
                logger.warning(
                    "chat_completion_thinking_only service=ollama request_type=%s model=%s thinking_chars=%s",
                    "pinned_fact_detector" if is_pinned_fact_detector else "chat",
                    self._model,
                    len(thinking.strip()),
                )
                raise ConfigurationError(
                    "Ollama chat response only included thinking content; set OLLAMA_CHAT_THINK=false "
                    "or increase OLLAMA_CHAT_MAX_TOKENS."
                )
        response_text = payload.get("response")
        if isinstance(response_text, str) and response_text.strip():
            logger.info(
                "chat_completion_response service=ollama request_type=%s model=%s answer_chars=%s used_field=response",
                "pinned_fact_detector" if is_pinned_fact_detector else "chat",
                self._model,
                len(response_text.strip()),
            )
            return response_text.strip()
        logger.warning(
            "chat_completion_missing_answer service=ollama request_type=%s model=%s payload_keys=%s",
            "pinned_fact_detector" if is_pinned_fact_detector else "chat",
            self._model,
            ",".join(sorted(str(key) for key in payload.keys())),
        )
        raise ConfigurationError("Ollama chat response did not include answer content.")


@lru_cache(maxsize=1)
def get_chat_completion_service() -> ChatCompletionService:
    settings = get_settings()
    if settings.e2e_shared_backends or settings.e2e_memory_backends:
        return DeterministicChatCompletionService()
    return OllamaChatCompletionService(settings)
