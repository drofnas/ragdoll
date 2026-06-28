from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass
from io import BytesIO
from typing import Iterable, TypeVar
from uuid import UUID

from docx import Document as DocxDocument
from pypdf import PdfReader

from ragdoll.core.instance_policy import resolve_instance_limits
from ragdoll.core.exceptions import ApplicationError

ALLOWED_EXTENSIONS = frozenset({"pdf", "docx", "md", "txt", "markdown"})
MAX_FILENAME_LENGTH = 255
DEFAULT_CHUNK_WORDS = 500
DEFAULT_CHUNK_OVERLAP_WORDS = 50
DEFAULT_CHUNK_MAX_CHARS = 2048
STATUS_BATCH_MAX_IDS = 100
PROCESSING_STAGES = ("parsing", "vector", "extraction", "graph")
ChunkT = TypeVar("ChunkT")

_upload_rate_limit_store: dict[str, deque[float]] = {}


@dataclass(frozen=True)
class UploadMetadata:
    filename: str
    file_type: str
    mime_type: str


@dataclass(frozen=True)
class TextChunk:
    text: str
    start_line: int


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


def enforce_upload_size_limit(*, file_size: int) -> None:
    limits = resolve_instance_limits()
    if limits.max_file_size_bytes is not None and file_size > limits.max_file_size_bytes:
        raise _usage_limit_error(
            detail=f"Uploaded file exceeds the {limits.max_file_size_bytes}-byte instance limit.",
            code="upload_file_too_large",
        )


def enforce_storage_limit(*, existing_storage_bytes: int, incoming_file_size: int) -> None:
    limits = resolve_instance_limits()
    if limits.storage_bytes is not None and existing_storage_bytes + incoming_file_size > limits.storage_bytes:
        raise _usage_limit_error(
            detail="This upload would exceed the configured storage limit for this instance.",
            code="storage_limit_exceeded",
        )


def enforce_document_limit(*, existing_document_count: int) -> None:
    limits = resolve_instance_limits()
    if limits.documents is not None and existing_document_count >= limits.documents:
        raise _usage_limit_error(
            detail="This account has reached the configured document limit for this instance.",
            code="document_limit_exceeded",
        )


def limit_chunks_for_instance(chunks: list[ChunkT]) -> list[ChunkT]:
    limits = resolve_instance_limits()
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
        "vector": "pending",
        "extraction": "pending",
        "graph": "pending",
        "detail": None,
    }


def validate_requested_stage(requested_stage: str) -> str:
    normalized = requested_stage.strip().lower()
    if normalized not in PROCESSING_STAGES:
        raise ApplicationError(
            f"Unsupported processing stage: {requested_stage}",
            status_code=400,
            title="Bad request",
            type_uri="https://ragdoll.dev/problems/bad-request",
            code="unsupported_processing_stage",
        )
    return normalized


def reset_processing_status_for_stage(payload: dict[str, str | None] | None, *, requested_stage: str) -> dict[str, str | None]:
    stage = validate_requested_stage(requested_stage)
    updated = dict(payload or build_processing_status_for_upload())
    updated["overall"] = "pending"
    updated["upload"] = "completed"
    started_reset = False
    for current_stage in PROCESSING_STAGES:
        if current_stage == stage:
            started_reset = True
        updated[current_stage] = "pending" if started_reset else "completed"
    updated["detail"] = None
    return updated


def mark_processing_stage_started(payload: dict[str, str | None] | None, *, requested_stage: str) -> dict[str, str | None]:
    stage = validate_requested_stage(requested_stage)
    updated = dict(payload or build_processing_status_for_upload())
    updated["overall"] = "processing"
    updated["upload"] = "completed"
    for current_stage in PROCESSING_STAGES:
        if current_stage == stage:
            updated[current_stage] = "processing"
            break
    updated["detail"] = None
    return updated


def mark_processing_stage_completed(
    payload: dict[str, str | None] | None,
    *,
    completed_stage: str,
) -> dict[str, str | None]:
    stage = validate_requested_stage(completed_stage)
    updated = dict(payload or build_processing_status_for_upload())
    updated["upload"] = "completed"
    updated[stage] = "completed"
    updated["detail"] = None
    updated["overall"] = "completed" if all(updated[name] == "completed" for name in PROCESSING_STAGES) else "processing"
    return updated


def mark_processing_stage_failed(
    payload: dict[str, str | None] | None,
    *,
    failed_stage: str,
    detail: str,
) -> dict[str, str | None]:
    stage = validate_requested_stage(failed_stage)
    updated = dict(payload or build_processing_status_for_upload())
    updated["overall"] = "failed"
    updated["upload"] = "completed"
    updated[stage] = "failed"
    updated["detail"] = detail[:500]
    return updated


def _line_tokens(text: str) -> list[tuple[str, int]]:
    tokens: list[tuple[str, int]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        tokens.extend((match.group(0), line_number) for match in re.finditer(r"\S+", line))
    if not tokens and text.strip():
        return [(text.strip(), 1)]
    return tokens


def _split_token_window(window_tokens: list[tuple[str, int]], *, max_chars: int) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    current_words: list[str] = []
    current_start_line = 1
    current_length = 0

    def flush_current() -> None:
        nonlocal current_words, current_start_line, current_length
        if current_words:
            chunks.append(TextChunk(text=" ".join(current_words), start_line=current_start_line))
            current_words = []
            current_start_line = 1
            current_length = 0

    for word, line_number in window_tokens:
        if len(word) > max_chars:
            flush_current()
            for index in range(0, len(word), max_chars):
                chunks.append(TextChunk(text=word[index : index + max_chars], start_line=line_number))
            continue

        next_length = len(word) if not current_words else current_length + 1 + len(word)
        if current_words and next_length > max_chars:
            flush_current()
            next_length = len(word)

        if not current_words:
            current_start_line = line_number
        current_words.append(word)
        current_length = next_length

    flush_current()
    return chunks


def chunk_text(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_WORDS,
    overlap: int = DEFAULT_CHUNK_OVERLAP_WORDS,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
) -> list[str]:
    return [chunk.text for chunk in chunk_text_with_lines(text, chunk_size=chunk_size, overlap=overlap, max_chars=max_chars)]


def chunk_text_with_lines(
    text: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_WORDS,
    overlap: int = DEFAULT_CHUNK_OVERLAP_WORDS,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
) -> list[TextChunk]:
    if max_chars <= 0:
        raise ValueError("max_chars must be positive.")
    tokens = _line_tokens(text)
    if not tokens:
        return []
    chunks: list[TextChunk] = []
    index = 0
    while index < len(tokens):
        window_tokens = tokens[index : index + chunk_size]
        if not window_tokens:
            break
        chunks.extend(_split_token_window(window_tokens, max_chars=max_chars))
        if index + chunk_size >= len(tokens):
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
