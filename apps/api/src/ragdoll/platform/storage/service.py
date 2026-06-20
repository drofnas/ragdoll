from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol
from urllib.parse import quote
from uuid import UUID

import httpx

from ragdoll.core.config import Settings, get_settings
from ragdoll.core.exceptions import ConfigurationError


class DocumentStorageService(Protocol):
    """Original-file storage plus derived-artifact cleanup hooks."""

    def store_original_file(self, storage_key: str, content: bytes, *, content_type: str | None = None) -> None: ...

    def download_original_file(self, storage_key: str) -> bytes: ...

    def delete_original_file(self, storage_key: str) -> bool: ...

    def delete_derived_artifacts(self, document_id: UUID, *, storage_prefix: str | None = None) -> bool: ...


@dataclass
class InMemoryDocumentStorage:
    originals: dict[str, bytes] = field(default_factory=dict)
    derived_prefixes: set[str] = field(default_factory=set)

    def store_original_file(self, storage_key: str, content: bytes, *, content_type: str | None = None) -> None:
        del content_type
        self.originals[storage_key] = content

    def download_original_file(self, storage_key: str) -> bytes:
        if storage_key not in self.originals:
            raise FileNotFoundError(storage_key)
        return self.originals[storage_key]

    def delete_original_file(self, storage_key: str) -> bool:
        return self.originals.pop(storage_key, None) is not None

    def delete_derived_artifacts(self, document_id: UUID, *, storage_prefix: str | None = None) -> bool:
        prefix = storage_prefix or f"derived/{document_id}"
        had_prefix = prefix in self.derived_prefixes
        self.derived_prefixes.discard(prefix)
        return had_prefix

    def seed_original_file(self, storage_key: str, content: bytes) -> None:
        self.originals[storage_key] = content


class UnconfiguredDocumentStorage:
    def _raise(self) -> None:
        raise ConfigurationError(
            "Storage configuration is not set. Configure Supabase storage before using document file operations."
        )

    def store_original_file(self, storage_key: str, content: bytes, *, content_type: str | None = None) -> None:
        del storage_key, content, content_type
        self._raise()

    def download_original_file(self, storage_key: str) -> bytes:
        del storage_key
        self._raise()

    def delete_original_file(self, storage_key: str) -> bool:
        del storage_key
        self._raise()

    def delete_derived_artifacts(self, document_id: UUID, *, storage_prefix: str | None = None) -> bool:
        del document_id, storage_prefix
        self._raise()


class SupabaseDocumentStorage:
    def __init__(self, settings: Settings) -> None:
        self._base_url = (settings.supabase_url or "").rstrip("/")
        self._service_role_key = (settings.supabase_service_role_key or "").strip()
        self._bucket = settings.effective_storage_bucket

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "authorization": f"Bearer {self._service_role_key}",
            "apikey": self._service_role_key,
        }

    def _object_url(self, storage_key: str) -> str:
        encoded_key = quote(storage_key.lstrip("/"), safe="/")
        return f"{self._base_url}/storage/v1/object/{self._bucket}/{encoded_key}"

    def store_original_file(self, storage_key: str, content: bytes, *, content_type: str | None = None) -> None:
        headers = dict(self._headers)
        if content_type:
            headers["content-type"] = content_type
        response = httpx.post(self._object_url(storage_key), headers=headers, content=content, timeout=10.0)
        response.raise_for_status()

    def download_original_file(self, storage_key: str) -> bytes:
        response = httpx.get(self._object_url(storage_key), headers=self._headers, timeout=10.0)
        if response.status_code == 404:
            raise FileNotFoundError(storage_key)
        response.raise_for_status()
        return response.content

    def delete_original_file(self, storage_key: str) -> bool:
        response = httpx.delete(self._object_url(storage_key), headers=self._headers, timeout=10.0)
        if response.status_code == 404:
            return False
        response.raise_for_status()
        return True

    def delete_derived_artifacts(self, document_id: UUID, *, storage_prefix: str | None = None) -> bool:
        del document_id, storage_prefix
        return False


@lru_cache(maxsize=1)
def get_document_storage() -> DocumentStorageService:
    settings = get_settings()
    if settings.e2e_memory_backends:
        return InMemoryDocumentStorage()
    if settings.has_storage_config:
        return SupabaseDocumentStorage(settings)
    return UnconfiguredDocumentStorage()
