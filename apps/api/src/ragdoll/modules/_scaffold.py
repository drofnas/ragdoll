"""Helpers for Phase 2 module scaffolds."""

from fastapi import APIRouter


def build_scaffold_router(prefix: str, tag: str) -> APIRouter:
    """Return an empty router mounted at the canonical module prefix."""
    return APIRouter(prefix=prefix, tags=[tag])
