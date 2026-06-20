import logging
import time
from uuid import uuid4

from fastapi import FastAPI, Request

from ragdoll.core.config import Settings

_LOGGING_CONFIGURED = False


def setup_logging(settings: Settings) -> None:
    """Configure application logging once per process."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    _LOGGING_CONFIGURED = True


def install_request_logging_middleware(app: FastAPI) -> None:
    """Install request logging and request-id propagation."""
    logger = logging.getLogger("ragdoll.api.request")

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        request.state.request_id = request_id
        started_at = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started_at) * 1000, 1)
        response.headers["x-request-id"] = request_id
        logger.info(
            "request_id=%s method=%s path=%s status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger."""
    return logging.getLogger(name)
