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


ENTITY_EXTRACTION_PROMPT = """Extract named entities from the provided chunk.
Return strict JSON with the shape {"entities":[{"surface_text":"...","normalized_name":"...","entity_type":"...","confidence_score":0.0}]}.
Use concise lowercase snake_case values for entity_type when possible.
Skip duplicates that refer to the same entity mention in the same chunk.
Chunk:
"""


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

    def _request_embed(self, texts: list[str]) -> list[list[float]]:
        if not self._base_url or not self._model:
            raise ConfigurationError("Ollama embedding configuration is incomplete.")

        payload = {"model": self._model, "input": texts}
        with httpx.Client(timeout=30.0) as client:
            response = client.post(f"{self._base_url}/api/embed", json=payload)
            if response.status_code == 404:
                response = client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": "\n".join(texts)},
                )
            response.raise_for_status()
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

    def extract_entities(self, text: str) -> list[ExtractedEntityCandidate]:
        if not self._base_url or not self._model:
            raise ConfigurationError("Ollama worker configuration is incomplete.")

        with httpx.Client(timeout=30.0) as client:
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

        payload = response.json()
        raw_response = payload.get("response")
        if not isinstance(raw_response, str):
            raise ConfigurationError("Ollama entity extraction response did not include a JSON body.")
        decoded = json.loads(raw_response)
        entries = decoded.get("entities", [])
        if not isinstance(entries, list):
            raise ConfigurationError("Ollama entity extraction response used an unexpected schema.")

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
            candidates.append(
                ExtractedEntityCandidate(
                    surface_text=surface_text[:255],
                    normalized_name=normalized_name[:255],
                    entity_type=entity_type[:80],
                    confidence_score=float(confidence) if confidence is not None else None,
                )
            )
        return candidates


@lru_cache(maxsize=1)
def get_embedding_generation_service() -> EmbeddingGenerationService:
    settings = get_settings()
    if settings.e2e_memory_backends:
        return DeterministicEmbeddingService()
    return OllamaEmbeddingService(settings)


@lru_cache(maxsize=1)
def get_entity_extraction_service() -> EntityExtractionService:
    settings = get_settings()
    if settings.e2e_memory_backends:
        return DeterministicEntityExtractionService()
    return OllamaEntityExtractionService(settings)
