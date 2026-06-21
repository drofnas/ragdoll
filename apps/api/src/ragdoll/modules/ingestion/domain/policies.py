from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass
from io import BytesIO
from typing import Iterable
from uuid import UUID

from docx import Document as DocxDocument
from pypdf import PdfReader

from ragdoll.core.exceptions import ApplicationError
from ragdoll.core.feature_flags import PlanTier
from ragdoll.modules.usage.domain.policies import resolve_plan_limits


ALLOWED_EXTENSIONS = frozenset({"pdf", "docx", "md", "txt", "markdown"})
MAX_FILENAME_LENGTH = 255
DEFAULT_CHUNK_WORDS = 500
DEFAULT_CHUNK_OVERLAP_WORDS = 50
DEFAULT_CHUNK_MAX_CHARS = 2048
STATUS_BATCH_MAX_IDS = 100

_upload_rate_limit_store: dict[str, deque[float]] = {}


@dataclass(frozen=True)
class UploadMetadata:
    filename: str
    file_type: str
    mime_type: str


def _usage_limit_error(*, detail: str, code: str) -> ApplicationError:
    return ApplicationError(
        detail,
        status_code=413,
        title="Upload rejected",
        type_uri="https://ragdoll.dev/problems/upload-rejected",
        code=code,
    )


def sanitize_filename(filename: str) -> str:
    if not filename or not filename.strip():
        raise ApplicationError(
            "A non-empty filename is required.",
            status_code=400,
            title="Bad request",
            type_uri="https://ragdoll.dev/problems/bad-request",
            code="invalid_filename",
        )

    normalized = filename.replace("\\", "/").strip()
    if "/" in normalized:
        normalized = normalized.split("/")[-1]
    if not normalized or normalized in {".", ".."} or ".." in normalized:
        raise ApplicationError(
            "The uploaded filename is invalid.",
            status_code=400,
            title="Bad request",
            type_uri="https://ragdoll.dev/problems/bad-request",
            code="invalid_filename",
        )

    if "." not in normalized:
        raise ApplicationError(
            "Uploaded files must include a supported extension.",
            status_code=400,
            title="Bad request",
            type_uri="https://ragdoll.dev/problems/bad-request",
            code="unsupported_file_type",
        )

    base, ext = normalized.rsplit(".", 1)
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ApplicationError(
            "This file type is not supported for manual uploads.",
            status_code=400,
            title="Bad request",
            type_uri="https://ragdoll.dev/problems/bad-request",
            code="unsupported_file_type",
        )

    safe_base = "".join(char if char.isalnum() or char in "._-" else "_" for char in base).strip("._-")
    if not safe_base:
        raise ApplicationError(
            "The uploaded filename is invalid.",
            status_code=400,
            title="Bad request",
            type_uri="https://ragdoll.dev/problems/bad-request",
            code="invalid_filename",
        )

    safe_name = f"{safe_base}.{ext}"
    if len(safe_name) > MAX_FILENAME_LENGTH:
        max_base = MAX_FILENAME_LENGTH - len(ext) - 1
        safe_name = f"{safe_base[:max_base].rstrip('._-')}.{ext}"
    return safe_name


def derive_upload_metadata(filename: str, declared_content_type: str | None) -> UploadMetadata:
    safe_name = sanitize_filename(filename)
    _, ext = safe_name.rsplit(".", 1)
    mime_type = (declared_content_type or "").strip().lower()
    default_mime_types = {
        "txt": "text/plain",
        "md": "text/markdown",
        "markdown": "text/markdown",
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    return UploadMetadata(
        filename=safe_name,
        file_type=ext,
        mime_type=mime_type or default_mime_types[ext],
    )


def enforce_upload_rate_limit(
    *,
    user_id: UUID,
    enabled: bool,
    max_requests: int,
    window_seconds: int,
    now: float | None = None,
) -> None:
    if not enabled:
        return
    current = time.monotonic() if now is None else now
    bucket = _upload_rate_limit_store.setdefault(str(user_id), deque())
    while bucket and current - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= max_requests:
        raise ApplicationError(
            "Too many uploads were started recently. Please try again shortly.",
            status_code=429,
            title="Too many requests",
            type_uri="https://ragdoll.dev/problems/rate-limit",
            code="upload_rate_limit_exceeded",
        )
    bucket.append(current)


def clear_upload_rate_limit_store_for_test() -> None:
    _upload_rate_limit_store.clear()


def enforce_upload_size_limit(*, file_size: int, plan_tier: str | PlanTier) -> None:
    limits = resolve_plan_limits(plan_tier)
    if limits.max_file_size_bytes is not None and file_size > limits.max_file_size_bytes:
        raise _usage_limit_error(
            detail=f"Uploaded file exceeds the {limits.max_file_size_bytes}-byte plan limit.",
            code="upload_file_too_large",
        )


def enforce_storage_limit(*, existing_storage_bytes: int, incoming_file_size: int, plan_tier: str | PlanTier) -> None:
    limits = resolve_plan_limits(plan_tier)
    if limits.storage_bytes is not None and existing_storage_bytes + incoming_file_size > limits.storage_bytes:
        raise _usage_limit_error(
            detail="This upload would exceed the current storage limit for the active plan.",
            code="storage_limit_exceeded",
        )


def enforce_document_limit(*, existing_document_count: int, plan_tier: str | PlanTier) -> None:
    limits = resolve_plan_limits(plan_tier)
    if limits.documents is not None and existing_document_count >= limits.documents:
        raise _usage_limit_error(
            detail="This account has reached the maximum number of stored documents for the active plan.",
            code="document_limit_exceeded",
        )


def limit_chunks_for_plan(chunks: list[str], *, plan_tier: str | PlanTier) -> list[str]:
    limits = resolve_plan_limits(plan_tier)
    return chunks[: limits.per_document_chunks]


def build_storage_key(*, owner_user_id: UUID, space_id: UUID, document_id: UUID, safe_filename: str) -> str:
    return f"documents/{owner_user_id}/{space_id}/{document_id}/{safe_filename}"


def build_preview_text(text: str, *, max_chars: int = 500) -> str | None:
    trimmed = text.strip()
    if not trimmed:
        return None
    return trimmed[:max_chars]


def build_processing_status_for_upload() -> dict[str, str | None]:
    return {
        "overall": "pending",
        "upload": "completed",
        "parsing": "pending",
        "vector": "deferred",
        "extraction": "deferred",
        "graph": "deferred",
        "detail": None,
    }


def mark_processing_started(payload: dict[str, str | None]) -> dict[str, str | None]:
    updated = dict(payload or build_processing_status_for_upload())
    updated["overall"] = "processing"
    updated["upload"] = "completed"
    updated["parsing"] = "processing"
    updated["vector"] = "deferred"
    updated["extraction"] = "deferred"
    updated["graph"] = "deferred"
    updated["detail"] = None
    return updated


def mark_processing_completed(payload: dict[str, str | None]) -> dict[str, str | None]:
    updated = dict(payload or build_processing_status_for_upload())
    updated["overall"] = "completed"
    updated["upload"] = "completed"
    updated["parsing"] = "completed"
    updated["vector"] = "deferred"
    updated["extraction"] = "deferred"
    updated["graph"] = "deferred"
    updated["detail"] = None
    return updated


def mark_processing_failed(payload: dict[str, str | None], detail: str) -> dict[str, str | None]:
    updated = dict(payload or build_processing_status_for_upload())
    updated["overall"] = "failed"
    updated["upload"] = "completed"
    updated["parsing"] = "failed"
    updated["vector"] = "deferred"
    updated["extraction"] = "deferred"
    updated["graph"] = "deferred"
    updated["detail"] = detail[:500]
    return updated


def _split_long_text(text: str, *, max_chars: int) -> list[str]:
    if len(text) <= max_chars:
        return [text]
    pieces: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= max_chars:
            pieces.append(remaining)
            break
        window = remaining[:max_chars]
        split_at = window.rfind(" ")
        if split_at <= 0:
            split_at = max_chars
        pieces.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].lstrip()
    return [piece for piece in pieces if piece]


def chunk_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_WORDS,
    overlap: int = DEFAULT_CHUNK_OVERLAP_WORDS,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive.")
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    index = 0
    while index < len(words):
        window_words = words[index : index + chunk_size]
        if not window_words:
            break
        joined = " ".join(window_words)
        chunks.extend(_split_long_text(joined, max_chars=max_chars))
        if index + chunk_size >= len(words):
            break
        index += max(1, chunk_size - overlap)
    return chunks


def extract_text_content(*, file_type: str, content: bytes) -> str:
    if file_type in {"txt", "md", "markdown"}:
        return content.decode("utf-8", errors="replace")
    if file_type == "pdf":
        reader = PdfReader(BytesIO(content))
        pages = [(page.extract_text() or "").strip() for page in reader.pages]
        return "\n\n".join(page for page in pages if page)
    if file_type == "docx":
        document = DocxDocument(BytesIO(content))
        paragraphs = [paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip()]
        return "\n\n".join(paragraphs)
    raise ApplicationError(
        "This file type is not supported for parsing.",
        status_code=400,
        title="Bad request",
        type_uri="https://ragdoll.dev/problems/bad-request",
        code="unsupported_file_type",
    )


def dedupe_document_ids(values: Iterable[UUID]) -> list[UUID]:
    seen: dict[UUID, None] = {}
    for value in values:
        seen.setdefault(value, None)
    return list(seen)
