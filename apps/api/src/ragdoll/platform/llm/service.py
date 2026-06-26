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
Return strict JSON matching the supplied schema.
Echo every input chunk_index exactly once.
Each chunk result must include the same chunk_index and an entities array.
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


@dataclass(frozen=True)
class ChunkExtractionRequest:
    chunk_index: int
    text: str


@dataclass(frozen=True)
class ChunkExtractionResult:
    chunk_index: int
    entities: list[ExtractedEntityCandidate]


class EmbeddingGenerationService(Protocol):
    def generate_embeddings(self, texts: list[str]) -> list[list[float]]: ...


class EntityExtractionService(Protocol):
    def extract_entities_batch(
        self, chunks: list[ChunkExtractionRequest]
    ) -> list[ChunkExtractionResult]: ...


class EntityExtractionError(RuntimeError):
    """Raised when the configured entity extractor cannot produce a valid result."""


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


def _entity_extraction_response_schema() -> dict[str, object]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "chunks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "chunk_index": {"type": "integer"},
                        "entities": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "properties": {
                                    "surface_text": {"type": "string"},
                                    "normalized_name": {"type": "string"},
                                    "entity_type": {"type": "string"},
                                    "confidence_score": {"type": ["number", "null"]},
                                },
                                "required": ["surface_text", "normalized_name", "entity_type"],
                            },
                        },
                    },
                    "required": ["chunk_index", "entities"],
                },
            }
        },
        "required": ["chunks"],
    }


def _normalize_extracted_entities(entries: object) -> list[ExtractedEntityCandidate]:
    if not isinstance(entries, list):
        raise EntityExtractionError("Ollama entity extraction response used an unexpected schema.")

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


def _validate_chunk_results(
    results: list[ChunkExtractionResult],
    *,
    requested_indexes: list[int],
) -> list[ChunkExtractionResult]:
    requested_index_set = set(requested_indexes)
    seen_indexes: set[int] = set()

    for result in results:
        if result.chunk_index not in requested_index_set:
            raise EntityExtractionError(
                f"Ollama entity extraction response returned an unexpected chunk_index: {result.chunk_index}."
            )
        if result.chunk_index in seen_indexes:
            raise EntityExtractionError(
                f"Ollama entity extraction response returned a duplicate chunk_index: {result.chunk_index}."
            )
        seen_indexes.add(result.chunk_index)

    missing_indexes = [index for index in requested_indexes if index not in seen_indexes]
    if missing_indexes:
        raise EntityExtractionError(
            "Ollama entity extraction response omitted requested chunk indexes: "
            + ", ".join(str(index) for index in missing_indexes)
            + "."
        )

    return sorted(results, key=lambda result: result.chunk_index)


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

    def extract_entities_batch(
        self,
        chunks: list[ChunkExtractionRequest],
    ) -> list[ChunkExtractionResult]:
        return [
            ChunkExtractionResult(
                chunk_index=chunk.chunk_index,
                entities=self.extract_entities(chunk.text),
            )
            for chunk in chunks
        ]


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
        return self.extract_entities_batch([ChunkExtractionRequest(chunk_index=0, text=text)])[0].entities

    def extract_entities_batch(
        self,
        chunks: list[ChunkExtractionRequest],
    ) -> list[ChunkExtractionResult]:
        if not chunks:
            return []
        if not self._base_url or not self._model:
            raise ConfigurationError("Ollama worker configuration is incomplete.")

        chunk_payload = {"chunks": [{"chunk_index": chunk.chunk_index, "text": chunk.text} for chunk in chunks]}
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": f"{ENTITY_EXTRACTION_PROMPT}{json.dumps(chunk_payload, ensure_ascii=True)}",
                        "stream": False,
                        "format": _entity_extraction_response_schema(),
                    },
                )
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise TimeoutError(
                f"Ollama entity extraction timed out after {self._timeout.read} seconds."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise EntityExtractionError(
                f"Ollama entity extraction request failed with status {exc.response.status_code}."
            ) from exc
        except httpx.HTTPError as exc:
            raise EntityExtractionError("Ollama entity extraction request failed.") from exc

        try:
            payload = response.json()
        except ValueError:
            raise EntityExtractionError("Ollama entity extraction returned a non-JSON envelope.")

        raw_response = payload.get("response")
        if not isinstance(raw_response, str):
            raise EntityExtractionError(
                "Ollama entity extraction response did not include a string JSON body."
            )
        decoded = _parse_ollama_json_body(raw_response)
        if decoded is None:
            raise EntityExtractionError("Ollama entity extraction returned malformed JSON.")
        entries = decoded.get("chunks")
        if not isinstance(entries, list):
            raise EntityExtractionError("Ollama entity extraction response used an unexpected schema.")

        results: list[ChunkExtractionResult] = []
        for entry in entries:
            if not isinstance(entry, dict):
                raise EntityExtractionError("Ollama entity extraction response used an unexpected schema.")
            chunk_index = entry.get("chunk_index")
            if not isinstance(chunk_index, int) or isinstance(chunk_index, bool):
                raise EntityExtractionError("Ollama entity extraction response used an unexpected schema.")
            results.append(
                ChunkExtractionResult(
                    chunk_index=chunk_index,
                    entities=_normalize_extracted_entities(entry.get("entities")),
                )
            )
        return _validate_chunk_results(
            results,
            requested_indexes=[chunk.chunk_index for chunk in chunks],
        )


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
    if settings.entity_extraction_mode == "deterministic":
        logger.info("entity_extraction_mode=deterministic; using deterministic extractor only.")
        return DeterministicEntityExtractionService()
    return OllamaEntityExtractionService(settings)
