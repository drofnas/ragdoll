from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import httpx

from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import ConfigurationError
from ragdoll.core.logging import get_logger


ENTITY_EXTRACTION_PROMPT = """Extract named entities from the provided chunk.
Return strict JSON with the shape {"entities":[{"surface_text":"...","normalized_name":"...","entity_type":"...","confidence_score":0.0}]}.
Use concise lowercase snake_case values for entity_type when possible.
Skip duplicates that refer to the same entity mention in the same chunk.
Chunk:
"""

logger = get_logger("ragdoll.platform.llm")


@dataclass(frozen=True)
class ExtractedEntityCandidate:
    surface_text: str
    normalized_name: str
    entity_type: str
    confidence_score: float | None = None


class EmbeddingGenerationService(Protocol):
    def generate_embeddings(self, texts: list[str]) -> list[list[float]]: ...


class EntityExtractionService(Protocol):
    def extract_entities(self, text: str) -> list[ExtractedEntityCandidate]: ...


def normalize_entity_name(value: str) -> str:
    lowered = re.sub(r"\s+", " ", value.strip().lower())
    return re.sub(r"[^a-z0-9 _-]", "", lowered).strip()


def _ollama_timeout(settings: Settings) -> httpx.Timeout:
    timeout_seconds = settings.ollama_worker_timeout_seconds
    return httpx.Timeout(connect=10.0, read=timeout_seconds, write=timeout_seconds, pool=timeout_seconds)


def _parse_ollama_json_body(raw_response: str) -> dict[str, object] | None:
    stripped = raw_response.strip()
    if not stripped:
        return None

    candidates = [stripped]

    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 3:
            candidates.append("\n".join(lines[1:-1]).strip())

    if "{" in stripped and "}" in stripped:
        candidates.append(stripped[stripped.find("{") : stripped.rfind("}") + 1].strip())

    for candidate in candidates:
        if not candidate:
            continue
        try:
            decoded = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, dict):
            return decoded

    return None


class DeterministicEmbeddingService:
    def __init__(self, *, dimensions: int = 8) -> None:
        self.dimensions = dimensions

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        embeddings: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            values = []
            for index in range(self.dimensions):
                pair = digest[(index * 2) % len(digest) : ((index * 2) % len(digest)) + 2]
                number = int.from_bytes(pair, "big", signed=False)
                values.append(round(number / 65535.0, 6))
            embeddings.append(values)
        return embeddings


class DeterministicEntityExtractionService:
    _pattern = re.compile(r"\b[A-Z][A-Za-z0-9]+(?:\s+[A-Z][A-Za-z0-9]+)*\b")

    def extract_entities(self, text: str) -> list[ExtractedEntityCandidate]:
        seen: dict[tuple[str, str], None] = {}
        candidates: list[ExtractedEntityCandidate] = []
        for match in self._pattern.finditer(text):
            surface_text = match.group(0).strip()
            normalized_name = normalize_entity_name(surface_text)
            if not normalized_name:
                continue
            entity_type = "proper_noun"
            key = (entity_type, normalized_name)
            if key in seen:
                continue
            seen[key] = None
            candidates.append(
                ExtractedEntityCandidate(
                    surface_text=surface_text,
                    normalized_name=normalized_name,
                    entity_type=entity_type,
                    confidence_score=0.75,
                )
            )
        return candidates


class OllamaEmbeddingService:
    def __init__(self, settings: Settings) -> None:
        self._base_url = (settings.ollama_worker_base_url_effective or "").rstrip("/")
        self._model = settings.ollama_embedding_model.strip()
        self._timeout = _ollama_timeout(settings)

    def _request_embed(self, texts: list[str]) -> list[list[float]]:
        if not self._base_url or not self._model:
            raise ConfigurationError("Ollama embedding configuration is incomplete.")

        payload = {"model": self._model, "input": texts}
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(f"{self._base_url}/api/embed", json=payload)
                if response.status_code == 404:
                    response = client.post(
                        f"{self._base_url}/api/embeddings",
                        json={"model": self._model, "prompt": "\n".join(texts)},
                    )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Ollama embedding generation timed out after {self._timeout.read} seconds."
            ) from exc
        body = response.json()
        if "embeddings" in body and isinstance(body["embeddings"], list):
            return [[float(component) for component in item] for item in body["embeddings"]]
        if "embedding" in body and isinstance(body["embedding"], list):
            return [[float(component) for component in body["embedding"]]]
        raise ConfigurationError("Ollama embedding response did not include embedding data.")

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self._request_embed(texts)
        if len(embeddings) != len(texts):
            raise ConfigurationError("Ollama returned an unexpected number of embeddings.")
        return embeddings


class OllamaEntityExtractionService:
    def __init__(self, settings: Settings) -> None:
        self._base_url = (settings.ollama_worker_base_url_effective or "").rstrip("/")
        self._model = settings.ollama_worker_model_effective.strip()
        self._timeout = _ollama_timeout(settings)

    def extract_entities(self, text: str) -> list[ExtractedEntityCandidate]:
        if not self._base_url or not self._model:
            raise ConfigurationError("Ollama worker configuration is incomplete.")

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": f"{ENTITY_EXTRACTION_PROMPT}{text}",
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Ollama entity extraction timed out after {self._timeout.read} seconds."
            ) from exc

        try:
            payload = response.json()
        except ValueError:
            logger.warning(
                "Ollama entity extraction returned a non-JSON envelope; falling back to deterministic extraction."
            )
            return DeterministicEntityExtractionService().extract_entities(text)

        raw_response = payload.get("response")
        if not isinstance(raw_response, str):
            logger.warning(
                "Ollama entity extraction response did not include a string JSON body; falling back to deterministic extraction."
            )
            return DeterministicEntityExtractionService().extract_entities(text)
        decoded = _parse_ollama_json_body(raw_response)
        if decoded is None:
            logger.warning(
                "Ollama entity extraction returned malformed JSON; falling back to deterministic extraction."
            )
            return DeterministicEntityExtractionService().extract_entities(text)
        entries = decoded.get("entities")
        if not isinstance(entries, list):
            logger.warning(
                "Ollama entity extraction response used an unexpected schema; falling back to deterministic extraction."
            )
            return DeterministicEntityExtractionService().extract_entities(text)

        candidates: list[ExtractedEntityCandidate] = []
        seen: dict[tuple[str, str], None] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            surface_text = str(entry.get("surface_text") or "").strip()
            normalized_name = normalize_entity_name(str(entry.get("normalized_name") or surface_text))
            entity_type = str(entry.get("entity_type") or "unknown").strip().lower() or "unknown"
            if not surface_text or not normalized_name:
                continue
            key = (entity_type, normalized_name)
            if key in seen:
                continue
            seen[key] = None
            confidence = entry.get("confidence_score")
            try:
                normalized_confidence = float(confidence) if confidence is not None else None
            except (TypeError, ValueError):
                normalized_confidence = None
            candidates.append(
                ExtractedEntityCandidate(
                    surface_text=surface_text[:255],
                    normalized_name=normalized_name[:255],
                    entity_type=entity_type[:80],
                    confidence_score=normalized_confidence,
                )
            )
        return candidates


@lru_cache(maxsize=1)
def get_embedding_generation_service() -> EmbeddingGenerationService:
    settings = get_settings()
    if settings.e2e_shared_backends:
        return DeterministicEmbeddingService(dimensions=settings.ollama_embedding_dimensions)
    if settings.e2e_memory_backends:
        return DeterministicEmbeddingService()
    return OllamaEmbeddingService(settings)


@lru_cache(maxsize=1)
def get_entity_extraction_service() -> EntityExtractionService:
    settings = get_settings()
    if settings.e2e_shared_backends:
        return DeterministicEntityExtractionService()
    if settings.e2e_memory_backends:
        return DeterministicEntityExtractionService()
    return OllamaEntityExtractionService(settings)
