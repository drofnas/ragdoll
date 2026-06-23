from __future__ import annotations

from ragdoll.core.exceptions import ApplicationError


def normalize_email_address(value: str) -> str:
    normalized = value.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise ApplicationError(
            "The request payload or parameters did not match the expected schema.",
            status_code=422,
            title="Request validation failed",
            type_uri="https://ragdoll.dev/problems/request-validation",
            code="request_validation_failed",
        )
    return normalized
